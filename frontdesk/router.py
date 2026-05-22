"""Lead → call routing.

Runs the pre-call gates Maya described on the 5/20 call, in order,
with wall-clock timing on every step so the UI can show the
sub-2-second budget visibly. Steps:

  1. Parse webhook payload (Yelp or Thumbtack)
  2. Consent / TCPA check (we don't call if they didn't opt in)
  3. Service area — match by CITY name (fast), fall back to nothing
     (zip-code lookup was rejected by Maya as too slow / fragile)
  4. Business hours — outside hours, queue instead of call
  5. Phone presence — no phone, send SMS / DM via the platform
  6. Slot availability — peek the (mocked) Google Sheet
  7. Agent selection — overflow chain by channel + language preference

Returns a Decision describing what happens next plus the per-step log.
The UI animates the log; the call itself is placed in main.py.

A note on timings: in production each external step (Yelp HMAC verify,
Sheets API, agent lookup) has real network latency. In the demo we
intentionally inject the same shape of latency so the < 2s budget is
honest — production swaps the mocks for real APIs at the same shape.
"""
from __future__ import annotations

import datetime as dt
import os
import time
from dataclasses import dataclass, field
from typing import Optional

from .agents import AGENTS, chain_for
from .leads import Lead
from .slots import all_slots, free_slots, is_within_business_hours, now_pacific
from .store import agent_status_snapshot


def business_hours_enabled() -> bool:
    """The business-hours gate is on unless BUSINESS_HOURS_ENABLED is a
    falsey value. Set BUSINESS_HOURS_ENABLED=false to call 24/7 (testing)."""
    return os.environ.get("BUSINESS_HOURS_ENABLED", "true").strip().lower() \
        not in ("0", "false", "no", "off")

# Simulated production latencies (ms) — each step would take roughly
# this long when wired to the real service it stands in for. Demo
# sleeps for these durations so the timing line matches reality.
_LATENCY_MS = {
    "parse":        12,   # webhook deserialize + HMAC verify
    "consent":       4,   # in-memory flag
    "service_area": 65,   # geocoder / city resolver (prod: Google Maps API)
    "hours":         3,   # datetime compare
    "phone":         2,   # E.164 check
    "slots":       240,   # Google Sheets API read (prod)
    "agent":        14,   # agent registry lookup + scoring
}

# Service area — cities + neighborhoods within ~25 miles of Safro Solutions.
# Maya rejected ZIP lookups as too slow / confusing; city match it is.
SERVICE_AREA_CITIES = {
    "beverly hills", "sherman oaks", "studio city", "valley glen",
    "burbank", "glendale", "pasadena", "north hollywood", "noho",
    "west hollywood", "encino", "tarzana", "van nuys", "reseda",
    "woodland hills", "los angeles", "la", "santa monica",
    "culver city", "marina del rey", "venice", "hollywood",
    "silver lake", "echo park", "downtown la", "dtla",
}


# ── Step log ────────────────────────────────────────────────────────────────

@dataclass
class Step:
    name: str
    label: str
    ok: bool
    detail: str
    ms: float            # wall-clock elapsed since lead arrival


@dataclass
class Decision:
    action: str          # "call" | "queue" | "sms" | "reject"
    reason: str          # human-readable reason
    agent_key: Optional[str] = None       # picked agent (only if action=call)
    chain_considered: list[str] = field(default_factory=list)
    queue_until: Optional[float] = None   # epoch when scheduler should fire
    steps: list[Step] = field(default_factory=list)
    total_ms: float = 0.0

    def total_seconds(self) -> float:
        return self.total_ms / 1000.0

    def as_dict(self) -> dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "agent_key": self.agent_key,
            "chain_considered": list(self.chain_considered),
            "queue_until": self.queue_until,
            "total_ms": round(self.total_ms, 1),
            "total_s": round(self.total_ms / 1000.0, 2),
            "budget_ms": 2000,
            "budget_hit": self.total_ms <= 2000,
            "steps": [
                {"name": s.name, "label": s.label, "ok": s.ok,
                 "detail": s.detail, "ms": round(s.ms, 1)}
                for s in self.steps
            ],
        }


# ── Router ──────────────────────────────────────────────────────────────────

def route(lead: Lead, now: Optional[dt.datetime] = None,
          simulate_latency: bool = True) -> Decision:
    t0 = time.perf_counter()
    steps: list[Step] = []

    def record(name: str, label: str, ok: bool, detail: str) -> None:
        if simulate_latency and name in _LATENCY_MS:
            time.sleep(_LATENCY_MS[name] / 1000.0)
        steps.append(Step(
            name=name, label=label, ok=ok, detail=detail,
            ms=(time.perf_counter() - t0) * 1000,
        ))

    # 1. Parse — the lead is already parsed by the caller; this step records
    #    that fact for the UI ("yelp webhook received → normalized").
    record("parse", f"{lead.source.title()} webhook received",
           True, f"lead id {lead.external_id} · {lead.display_name() or '(no name)'}")

    # 2. Consent / TCPA gate.
    if not lead.consent_call:
        record("consent", "TCPA consent check", False,
               "no call opt-in on form — sending text instead")
        return _decide("sms", "no call consent",
                       chain=[], steps=steps, t0=t0)
    record("consent", "TCPA consent check", True, "caller opted in to phone")

    # 3. Service area — city match.
    city = (lead.city or "").strip().lower()
    in_area = any(c in city or city in c for c in SERVICE_AREA_CITIES) if city else False
    if not in_area:
        record("service_area", f"Service area: {lead.city or '(no city)'}",
               False, "outside ~25 mi radius — out of area")
        return _decide("reject", "out of service area",
                       chain=[], steps=steps, t0=t0)
    record("service_area", f"Service area: {lead.city}",
           True, "in coverage (≤25 mi)")

    # 4. Business hours — Maya: do NOT call after hours, queue instead.
    #    Timezone is the business's own (Pacific), not the server's (UTC).
    now = now or now_pacific()
    if not business_hours_enabled():
        record("hours", f"Business hours: {now.strftime('%H:%M').strip()} PT",
               True, "check disabled (BUSINESS_HOURS_ENABLED=false) — calling 24/7")
    elif not is_within_business_hours(now):
        next_open = _next_open(now)
        record("hours", f"Business hours: {now.strftime('%H:%M').strip()} PT",
               False, f"after hours — queued for {next_open.strftime('%a %H:%M')}")
        return _decide("queue", "outside business hours",
                       chain=[], steps=steps, t0=t0,
                       queue_until=next_open.timestamp())
    else:
        record("hours", f"Business hours: {now.strftime('%H:%M').strip()} PT",
               True, "within 7 AM – 7 PM Pacific")

    # 5. Phone presence — without a number we can't dial.
    if not lead.phone:
        record("phone", "Phone number on lead", False,
               "no phone — sending text via Yelp / SMS instead")
        return _decide("sms", "no phone on form",
                       chain=[], steps=steps, t0=t0)
    record("phone", "Phone number on lead", True, lead.phone)

    # 6. Slot availability — fast peek of the (mocked) Google Sheet.
    free = free_slots()
    if not free:
        record("slots", "Technician slots", False,
               "no slots free — flagging dispatcher")
        return _decide("reject", "no technician availability",
                       chain=[], steps=steps, t0=t0)
    sample = free[0]
    record("slots", "Technician slots (Google Sheet)", True,
           f"{len(free)} free · earliest {sample.technician} · "
           f"{sample.day_label} {sample.window}")

    # 7. Agent selection — overflow chain by channel + language hint.
    prefers_spanish = lead.language_hint.startswith("es")
    chain = chain_for("outbound", prefers_spanish=prefers_spanish)
    statuses = agent_status_snapshot()
    picked: Optional[str] = None
    for key in chain:
        s = statuses.get(key, {"status": "idle"})
        if s["status"] == "idle":
            picked = key
            break
    if not picked:
        record("agent", "Agent rotation", False,
               f"all agents busy · queueing for next free in {chain[0]}")
        return _decide("queue", "all agents busy",
                       chain=chain, steps=steps, t0=t0,
                       queue_until=time.time() + 30)

    agent = AGENTS[picked]
    notes = ", ".join(
        f"{k}={statuses.get(k, {}).get('status', 'idle')}" for k in chain
    )
    record("agent", f"Agent → {agent.name}", True,
           f"chain ({', '.join(chain)}) → picked {picked} · {notes}")

    return _decide("call", f"placing call via {agent.name}",
                   chain=chain, steps=steps, t0=t0, agent_key=picked)


def _decide(action: str, reason: str, *, chain: list[str], steps: list[Step],
            t0: float, agent_key: Optional[str] = None,
            queue_until: Optional[float] = None) -> Decision:
    total = (time.perf_counter() - t0) * 1000
    return Decision(
        action=action, reason=reason, agent_key=agent_key,
        chain_considered=chain, queue_until=queue_until,
        steps=steps, total_ms=total,
    )


def _next_open(now: dt.datetime) -> dt.datetime:
    from .slots import BUSINESS_OPEN_HOUR, BUSINESS_CLOSE_HOUR
    candidate = now.replace(hour=BUSINESS_OPEN_HOUR, minute=0, second=0,
                             microsecond=0)
    if now.hour >= BUSINESS_CLOSE_HOUR:
        candidate += dt.timedelta(days=1)
    elif now.hour < BUSINESS_OPEN_HOUR:
        pass
    else:
        candidate = now
    return candidate
