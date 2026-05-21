"""FastAPI app — Safro Solutions AI dispatcher.

Two surfaces:
  /         → ops dashboard (the demo Maya asked for):
              lead → router (<2s budget) → Vapi web call → booking.
  /console  → the original chat console (Amanda inbound, useful as
              fallback when there's no microphone, no Vapi key, etc.).
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .agents import AGENTS, COMPANY, DIAGNOSTIC_FEE_USD, REQUIRED_FIELDS
from .leads import (
    SAMPLE_LEADS,
    Lead,
    from_thumbtack_webhook,
    from_yelp_webhook,
    sample_by_key,
)
from .pipeline import handle_turn as console_handle_turn
from .pipeline import start_call as console_start_call
from .pipeline import trigger_outbound as console_trigger_outbound
from .router import SERVICE_AREA_CITIES, route
from .scenarios import SCENARIOS
from .scheduler import (
    enqueue,
    history_snapshot,
    queue_snapshot,
    record_attempt,
    schedule_retry,
)
from .slots import all_slots, book as book_slot, free_slots
from .store import (
    CallRecord,
    LeadRecord,
    add_booking,
    add_call,
    add_lead,
    agent_status_snapshot,
    append_transcript,
    bookings,
    bump_agent_counts,
    call_snapshot,
    escalations,
    get_call,
    get_lead,
    leads_snapshot,
    log_escalation,
    recent_calls,
    reset_demo as store_reset,
    set_agent_status,
    set_call_status,
    update_lead_call,
)
from .sms import send_sms
from .store import Booking
from .telegram import broadcast_booking, handle_update, set_webhook
from .transcript import parse_transcript, transcript_text_of
from .ui import OPS_HTML
from .ui_console import INDEX_HTML as CONSOLE_HTML
from .vapi_client import is_configured as vapi_configured
from .vapi_client import parse_webhook as vapi_parse
from .vapi_client import public_key as vapi_public_key
from .vapi_client import web_call_config

app = FastAPI(title="Safro Dispatcher", version="3.0.0")

BOT_HANDLE = "inbound_call_bot"
DEMO_PHONE = "+1 (747) 900-2649"


# ─── Health + config ────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "company": COMPANY,
        "agents": list(AGENTS.keys()),
        "bookings": len(bookings()),
        "escalations": len(escalations()),
        "telegram_live": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "llm_live": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "vapi_live": vapi_configured(),
    }


@app.get("/api/config")
def config() -> dict:
    return {
        "company": COMPANY,
        "fee": DIAGNOSTIC_FEE_USD,
        "demo_phone": DEMO_PHONE,
        "telegram_bot": BOT_HANDLE,
        "fields": [{"key": k, "label": label} for k, label in REQUIRED_FIELDS],
        "service_area_cities": sorted(SERVICE_AREA_CITIES),
        "agents": [
            {
                "key": a.key, "name": a.name, "voice": a.voice_style,
                "channel": a.channel, "opening": a.opening_line,
                "languages": a.languages,
            }
            for a in AGENTS.values()
        ],
        "sample_leads": [
            {"key": s["key"], "label": s["label"], "summary": s["summary"],
             "tag": s["tag"]}
            for s in SAMPLE_LEADS
        ],
        "scenarios": [
            {"key": s.key, "title": s.title, "tag": s.tag,
             "agent": s.agent, "summary": s.summary}
            for s in SCENARIOS
        ],
        "telegram_live": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "llm_live": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "vapi_live": vapi_configured(),
        "vapi_public_key": vapi_public_key() or "",
    }


# ─── Ops dashboard: lead intake → routing → call ────────────────────────────

class LeadSimReq(BaseModel):
    key: str
    auto_call: bool = True   # if True and decision==call, immediately start agent


@app.post("/api/leads/simulate")
def leads_simulate(r: LeadSimReq) -> dict:
    import datetime as _dt
    sample = sample_by_key(r.key)
    if not sample:
        return JSONResponse({"error": "unknown sample lead"}, status_code=404)
    if sample["payload"].get("project_id", "").startswith("thumbtack"):
        lead = from_thumbtack_webhook(_thumbtack_shape(sample["payload"]))
    else:
        lead = from_yelp_webhook(sample["payload"])

    # Clear any "simulated previous call" force_busy from prior scenarios so
    # the rollover demo doesn't leak between clicks.
    for k, a in agent_status_snapshot().items():
        if a.get("current_call_id") == "sim-prev-call":
            set_agent_status(k, "idle")

    # Demo overrides:
    #  • force_hour/force_minute  → pretend this lead arrived at a specific
    #    local time, so the after-hours queue path is visible during a daytime demo.
    #  • force_busy               → mark the listed agents BUSY before routing,
    #    so the overflow chain (Tony busy → Sofia) is visible on a single click.
    forced_now = None
    if "force_hour" in sample:
        now = _dt.datetime.now().replace(
            hour=sample["force_hour"],
            minute=sample.get("force_minute", 0),
            second=0, microsecond=0,
        )
        forced_now = now

    for agent_key in sample.get("force_busy", []):
        set_agent_status(agent_key, "busy",
                          call_id="sim-prev-call",
                          lead_id="sim-prev-lead")

    return _ingest_lead(lead, sample_label=sample["label"], force_now=forced_now)


@app.post("/api/leads/webhook")
async def leads_webhook(request: Request) -> dict:
    """Generic webhook receiver — accepts both Yelp and Thumbtack shapes."""
    body = await request.json()
    if isinstance(body, dict) and ("consumer" in body or "project_text" in body):
        lead = from_yelp_webhook(body)
    elif isinstance(body, dict) and "request" in body:
        lead = from_thumbtack_webhook(body)
    else:
        return JSONResponse({"error": "unrecognized payload"}, status_code=400)
    return _ingest_lead(lead)


def _thumbtack_shape(yelp_payload: dict) -> dict:
    """Light translator so a sample 'thumbtack' lead actually parses through
    the thumbtack adapter — keeps the demo honest about payload shapes."""
    c = yelp_payload.get("consumer", {})
    return {
        "requestPk": yelp_payload.get("project_id"),
        "request": {
            "firstName": c.get("first_name", ""),
            "lastName": c.get("last_name", ""),
            "phoneNumber": c.get("phone"),
            "city": c.get("city", ""),
            "description": yelp_payload.get("project_text", ""),
            "language": yelp_payload.get("language", "en"),
            "phoneConsent": c.get("opt_in_call", True),
        },
    }


def _ingest_lead(lead: Lead, sample_label: str = "",
                 force_now: Optional[object] = None) -> dict:
    """Common path for both simulated + real webhook leads: run the router,
    record, alert, return decision."""
    lead_id = f"ld_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    decision = route(lead, now=force_now)

    rec = LeadRecord(
        lead_id=lead_id, source=lead.source, received_at=lead.received_at,
        customer_name=lead.display_name() or "(no name)",
        phone=lead.phone, city=lead.city,
        appliance_hint=lead.appliance_hint,
        language=lead.language_hint, consent=lead.consent_call,
        decision=decision.as_dict(),
        queue_reason=decision.reason if decision.action == "queue" else None,
    )
    add_lead(rec)

    # Telegram alert per outcome — Maya wants every lead to fire a notification.
    _alert_lead(rec, decision, sample_label or lead.appliance_hint)

    # Queue handling — store the lead for later firing.
    if decision.action == "queue":
        enqueue(lead_id, rec.customer_name + " · " + (rec.phone or "no-phone"),
                decision.queue_until or (time.time() + 30),
                reason=decision.reason)

    return {
        "lead_id": lead_id,
        "lead": _serialize_lead(lead),
        "decision": decision.as_dict(),
    }


def _serialize_lead(lead: Lead) -> dict:
    return {
        "source": lead.source, "external_id": lead.external_id,
        "name": lead.display_name(), "phone": lead.phone,
        "city": lead.city, "appliance_hint": lead.appliance_hint,
        "language": lead.language_hint, "consent": lead.consent_call,
    }


def _alert_lead(rec: LeadRecord, decision, label: str) -> None:
    icon = {"call": "📞", "queue": "⏰", "sms": "💬", "reject": "🚫"}[decision.action]
    head = f"{icon}  Lead {rec.source.upper()} · {rec.customer_name}"
    bits = [head,
            f"Phone: {rec.phone or '(none)'}",
            f"City:  {rec.city}",
            f"Need:  {label or rec.appliance_hint}",
            f"Decision: {decision.action.upper()} · {decision.reason}",
            f"Routing: {decision.total_ms:.0f} ms (budget 2000 ms)"]
    if decision.agent_key:
        ag = AGENTS[decision.agent_key].name
        bits.append(f"Agent: {ag}")
    broadcast_booking("\n".join(bits))


# ─── Vapi web-call lifecycle ────────────────────────────────────────────────

class VapiStartReq(BaseModel):
    lead_id: str
    # Optional inline payload — Vercel serverless cold starts wipe the
    # in-memory `_leads` dict between requests, so the browser also passes
    # the lead/decision back. Whichever path has the data wins.
    lead: Optional[dict] = None
    decision: Optional[dict] = None


@app.post("/api/vapi/start")
def vapi_start(r: VapiStartReq) -> dict:
    """Return the inline Vapi assistant config so the browser SDK can start
    the call. Marks the chosen agent BUSY for the duration."""
    rec = get_lead(r.lead_id)
    decision = rec.decision if rec else (r.decision or {})
    lead_payload = (None if rec else r.lead) or (
        {"source": rec.source, "name": rec.customer_name, "phone": rec.phone,
         "city": rec.city, "appliance_hint": rec.appliance_hint,
         "language": rec.language, "consent": rec.consent} if rec else None
    )

    if not decision or decision.get("action") != "call" or not decision.get("agent_key"):
        return JSONResponse(
            {"error": "no call action for this lead",
             "have_rec": bool(rec), "have_inline": bool(r.decision)},
            status_code=400,
        )
    if not lead_payload:
        return JSONResponse(
            {"error": "no lead payload (server has no memory of lead_id and "
                       "browser didn't pass one inline)"},
            status_code=400,
        )

    agent = AGENTS[decision["agent_key"]]
    name = lead_payload.get("name") or ""
    parts = name.split(" ", 1)
    lead = Lead(
        source=lead_payload.get("source", "yelp"), external_id=r.lead_id,
        received_at=time.time(),
        customer_first_name=parts[0] if parts else "",
        customer_last_name=parts[1] if len(parts) > 1 else "",
        phone=lead_payload.get("phone"),
        city=lead_payload.get("city", ""),
        appliance_hint=lead_payload.get("appliance_hint", ""),
        language_hint=lead_payload.get("language", "en"),
        consent_call=bool(lead_payload.get("consent", True)),
    )

    # If the server didn't have the lead in memory, add it now so subsequent
    # calls on this warm instance find it.
    if not rec:
        add_lead(LeadRecord(
            lead_id=r.lead_id, source=lead.source, received_at=lead.received_at,
            customer_name=name or "(no name)", phone=lead.phone, city=lead.city,
            appliance_hint=lead.appliance_hint, language=lead.language_hint,
            consent=lead.consent_call, decision=decision,
        ))

    assistant = web_call_config(agent, lead)
    call_id = f"cl_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    add_call(CallRecord(
        call_id=call_id, lead_id=r.lead_id, agent_key=agent.key,
        started_at=time.time(), status="initiating",
    ))
    update_lead_call(r.lead_id, call_id)
    set_agent_status(agent.key, "busy", call_id=call_id, lead_id=r.lead_id)
    bump_agent_counts(agent.key)

    return {
        "call_id": call_id,
        "agent": {"key": agent.key, "name": agent.name,
                  "voice_style": agent.voice_style},
        "assistant": assistant,
        "public_key": vapi_public_key() or "",
        "vapi_configured": vapi_configured(),
    }


class VapiEventReq(BaseModel):
    call_id: str
    kind: str                    # "ringing" | "in_progress" | "ended"
    role: Optional[str] = None    # for transcript chunks
    text: Optional[str] = None
    vapi_call_id: Optional[str] = None
    outcome: Optional[str] = None
    transcript: Optional[str] = None
    # Cold-start recovery — the browser passes these so we can recreate
    # call + lead state on a fresh serverless instance.
    agent_key: Optional[str] = None
    lead_id: Optional[str] = None
    lead: Optional[dict] = None


@app.post("/api/vapi/event")
def vapi_event(r: VapiEventReq) -> dict:
    """Browser-side bridge for Vapi SDK events → our store.

    The web SDK fires events in-page; the page POSTs them here so the
    server can advance state + the dashboard can poll a single source.
    """
    c = get_call(r.call_id)
    if not c:
        # Cold start — rehydrate from inline payload if the browser sent one.
        if r.agent_key and r.lead_id:
            c = CallRecord(call_id=r.call_id, lead_id=r.lead_id,
                            agent_key=r.agent_key, started_at=time.time(),
                            status="initiating")
            add_call(c)
            if r.lead and not get_lead(r.lead_id):
                add_lead(LeadRecord(
                    lead_id=r.lead_id,
                    source=r.lead.get("source", "yelp"),
                    received_at=time.time(),
                    customer_name=r.lead.get("name") or "(no name)",
                    phone=r.lead.get("phone"),
                    city=r.lead.get("city", ""),
                    appliance_hint=r.lead.get("appliance_hint", ""),
                    language=r.lead.get("language", "en"),
                    consent=bool(r.lead.get("consent", True)),
                ))
        else:
            return JSONResponse({"error": "unknown call",
                                 "hint": "browser must include agent_key + lead_id "
                                          "on the ended event for cold-start recovery"},
                                status_code=404)

    if r.kind == "transcript" and r.text:
        append_transcript(r.call_id, r.role or "assistant", r.text)
        set_call_status(r.call_id, "in_progress",
                        vapi_call_id=r.vapi_call_id)
    elif r.kind in ("ringing", "in_progress"):
        set_call_status(r.call_id, r.kind, vapi_call_id=r.vapi_call_id)
    elif r.kind == "ended":
        outcome = r.outcome or "answered"
        set_call_status(r.call_id, "ended", outcome=outcome,
                        vapi_call_id=r.vapi_call_id)
        set_agent_status(c.agent_key, "idle")
        record_attempt(c.lead_id, outcome, c.agent_key)

        finalize_result: dict = {}

        # If the call didn't actually connect → schedule retry.
        if outcome in ("no_answer", "busy", "failed"):
            attempts = sum(
                1 for h in history_snapshot()
                if h["lead_id"] == c.lead_id and h["outcome"] in
                ("answered", "no_answer", "busy", "failed")
            )
            schedule_retry(c.lead_id, f"retry call to lead {c.lead_id}",
                           attempts_so_far=attempts)
            finalize_result = {"action": "retry_scheduled"}
        elif outcome == "answered":
            # Parse the transcript into a booking record (Anthropic). The
            # transcript is preferred from the explicit field; fall back to
            # the streamed chunks the browser bridge already saved.
            text = r.transcript or transcript_text_of(c.transcript)
            print(f"[finalize] call={r.call_id} transcript_len={len(text)}")
            finalize_result = _finalize_call(c, text)
        return {"ok": True, "call": call_snapshot(r.call_id),
                "finalize": finalize_result}
    return {"ok": True, "call": call_snapshot(r.call_id)}


def _finalize_call(call: CallRecord, transcript_text: str) -> dict:
    """Run Anthropic transcript-parse, write Booking + send confirmations
    OR log escalation. Returns a dict the UI can render so the user sees
    exactly what happened on the server (booked / parse_failed / missing fields)."""
    if not transcript_text.strip():
        return {"action": "no_transcript",
                "message": "Call ended with no transcript captured."}

    parsed = parse_transcript(transcript_text)
    if not parsed:
        return {"action": "parse_failed",
                "message": "Couldn't parse the transcript (LLM unavailable or invalid output). "
                           "Telegram/booking skipped."}

    if parsed.get("escalation"):
        from .agents import ESCALATION_REASONS
        reason = parsed["escalation"]
        log_escalation(call.lead_id, call.agent_key, reason,
                        f"escalation during call {call.call_id}")
        broadcast_booking(
            f"⚠ Escalation — {ESCALATION_REASONS.get(reason, reason)}\n"
            f"Agent: {AGENTS[call.agent_key].name}\n"
            f"Lead: {call.lead_id}\n"
            f"Route to dispatcher."
        )
        return {"action": "escalation", "reason": reason,
                "message": f"Escalated: {ESCALATION_REASONS.get(reason, reason)}"}

    fields = parsed.get("fields", {}) or {}

    # Merge the lead-form seed into the parsed fields. The agent often
    # skips re-asking for what's already on the form (per the system
    # prompt), so the transcript won't contain the customer's phone or
    # name verbatim — but the form did. Without this merge, every
    # outbound booking fails for "missing phone".
    lead = get_lead(call.lead_id)
    if lead:
        if lead.phone and not str(fields.get("phone", "")).strip():
            fields["phone"] = lead.phone
        if lead.customer_name and not str(fields.get("name", "")).strip():
            fields["name"] = lead.customer_name
        if lead.appliance_hint and not str(fields.get("problem", "")).strip():
            fields["problem"] = lead.appliance_hint

    parsed["fields"] = fields

    # Re-evaluate the booked condition with seeded fields in place.
    from .transcript import _REQUIRED_FOR_BOOK
    missing = [k for k in _REQUIRED_FOR_BOOK
               if k != "fee_agreed" and not str(fields.get(k, "")).strip()]
    fee_ok = bool(fields.get("fee_agreed", False))
    if not missing and fee_ok and not parsed.get("escalation"):
        parsed["booked"] = True

    if not parsed.get("booked"):
        return {
            "action": "not_booked",
            "fields": fields,
            "missing_required": missing,
            "fee_agreed": fee_ok,
            "message": (
                f"Parsed the call but didn't create a booking. "
                f"Missing required: {missing or 'none'}. fee_agreed={fee_ok}."
            ),
        }

    bid = f"bk_{int(time.time() * 1000) % 10_000_000:x}"
    b = Booking(
        id=bid, caller=call.lead_id, agent=call.agent_key,
        channel=AGENTS[call.agent_key].channel,
        name=str(fields.get("name", "") or ""),
        phone=str(fields.get("phone", "") or ""),
        address=str(fields.get("address", "") or ""),
        appliance=str(fields.get("appliance", "") or ""),
        brand=str(fields.get("brand", "") or ""),
        model=str(fields.get("model", "") or ""),
        problem=str(fields.get("problem", "") or ""),
        window=str(fields.get("window", "") or ""),
        access=str(fields.get("access", "") or ""),
        fee_agreed=bool(fields.get("fee_agreed", False)),
        slot_key=parsed.get("slot_key", "") or "",
        lead_id=call.lead_id,
    )
    add_booking(b)
    bump_agent_counts(call.agent_key, booked=True)
    if b.slot_key:
        try:
            from .slots import book as book_slot_real
            book_slot_real(b.slot_key, b.id, caller=call.lead_id)
        except Exception:
            pass

    tg = broadcast_booking(
        f"📞 New booking — {COMPANY}\n"
        f"Agent: {AGENTS[call.agent_key].name}\n"
        f"Customer: {b.name}\n"
        f"Phone: {b.phone}\n"
        f"Address: {b.address}\n"
        f"Appliance: {b.appliance} · {b.brand} · model {b.model or 'n/a'}\n"
        f"Problem: {b.problem}\n"
        f"Window: {b.window}\n"
        f"Access: {b.access or '—'}\n"
        f"Fee accepted: yes · Ref: {b.id}"
    )
    sms_result = "skipped"
    if b.phone:
        sms_result = send_sms(b.phone,
                  f"{COMPANY}: you're booked for {b.window}. "
                  f"Diagnostic fee ${DIAGNOSTIC_FEE_USD} accepted. Ref {b.id}.")
    return {"action": "booked", "booking": b.__dict__,
            "telegram": tg, "sms": sms_result,
            "message": f"Booking created — ref {b.id}"}


@app.post("/api/vapi/webhook")
async def vapi_webhook(request: Request) -> dict:
    """Direct webhook from Vapi (production path).

    Wired up here so production traffic from Vapi hits the same code as
    the browser bridge. Best-effort: missing fields just no-op.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"ok": False}
    evt = vapi_parse(payload)
    # Tied to call by vapi_call_id — we don't always know our call_id here.
    # The browser bridge keeps state authoritative for the demo.
    return {"ok": True, "kind": evt.get("kind")}


# ─── Lead / queue / agent / call snapshots for the dashboard poll ──────────

@app.get("/api/leads")
def api_leads() -> dict:
    return {"leads": leads_snapshot()}


@app.get("/api/leads/{lead_id}")
def api_lead(lead_id: str) -> dict:
    rec = get_lead(lead_id)
    if not rec:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"lead": rec.__dict__}


@app.get("/api/agents/status")
def api_agents_status() -> dict:
    return {"agents": agent_status_snapshot()}


@app.get("/api/queue")
def api_queue() -> dict:
    return {"queued": queue_snapshot(), "history": history_snapshot()}


@app.get("/api/calls/{call_id}")
def api_call(call_id: str) -> dict:
    snap = call_snapshot(call_id)
    if not snap:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {"call": snap}


@app.get("/api/calls")
def api_calls() -> dict:
    return {"calls": recent_calls()}


@app.get("/api/slots")
def api_slots() -> dict:
    """Mock 'Google Sheet' panel — every slot row, with current booked/held state."""
    return {
        "slots": [
            {"technician": s.technician, "day": s.day_label, "window": s.window,
             "free": s.free, "booked_by": s.booked_by, "held_for": s.held_for,
             "key": s.key()}
            for s in all_slots()
        ],
        "free_count": len(free_slots()),
    }


@app.post("/api/demo/reset")
def demo_reset() -> dict:
    from .slots import reset_demo as slots_reset
    from .scheduler import reset_demo as sched_reset
    store_reset()
    slots_reset()
    sched_reset()
    return {"ok": True}


@app.post("/api/agents/reset")
def agents_reset() -> dict:
    """Free every agent without clearing bookings / queue / sheet.

    Browser calls this on page load so a refresh always gives a clean
    agent floor — useful when a previous test left an agent busy.
    """
    for k in agent_status_snapshot().keys():
        set_agent_status(k, "idle")
    return {"ok": True, "agents": agent_status_snapshot()}


# ─── Legacy chat console (Amanda inbound, no Vapi needed) ──────────────────

class StartReq(BaseModel):
    agent: str = "amanda"
    caller: str = "web-demo"


@app.post("/api/console/start")
def console_start(r: StartReq) -> dict:
    return console_start_call(r.caller, r.agent)


class TurnReq(BaseModel):
    agent: str = "amanda"
    caller: str = "web-demo"
    text: str


@app.post("/api/console/turn")
def console_turn(r: TurnReq) -> dict:
    return console_handle_turn(r.caller, r.text, r.agent)


class OutboundReq(BaseModel):
    name: str = "Daniel Park"
    phone: str = "+1 415 555 0188"
    problem: str = "Whirlpool dryer not heating"


@app.post("/api/console/outbound")
def console_outbound(r: OutboundReq) -> dict:
    return console_trigger_outbound(r.name, r.phone, r.problem)


@app.get("/api/scenarios/{key}")
def api_scenario(key: str) -> dict:
    s = next((s for s in SCENARIOS if s.key == key), None)
    if not s:
        return JSONResponse({"error": "unknown scenario"}, status_code=404)
    return {"key": s.key, "title": s.title, "tag": s.tag, "agent": s.agent,
            "summary": s.summary, "seed": s.seed, "lines": s.lines}


@app.get("/api/bookings")
def api_bookings() -> dict:
    return {"bookings": [b.__dict__ for b in bookings()]}


@app.get("/api/escalations")
def api_escalations() -> dict:
    return {"escalations": escalations()}


# ─── Telegram passthrough ──────────────────────────────────────────────────

@app.post("/telegram/webhook")
async def tg_webhook(request: Request) -> JSONResponse:
    try:
        handle_update(await request.json())
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.get("/admin/set-webhook")
def admin_set_webhook(request: Request) -> dict:
    base = str(request.base_url).rstrip("/")
    return set_webhook(base)


# ─── HTML routes ───────────────────────────────────────────────────────────

def _subst(html: str) -> str:
    return (html
            .replace("__BOT__", BOT_HANDLE)
            .replace("__PHONE__", DEMO_PHONE)
            .replace("__COMPANY__", COMPANY)
            .replace("__FEE__", str(DIAGNOSTIC_FEE_USD)))


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _subst(OPS_HTML)


@app.get("/console", response_class=HTMLResponse)
def console() -> str:
    return _subst(CONSOLE_HTML)
