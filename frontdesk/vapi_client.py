"""Vapi web-call integration.

For the demo we run Vapi in browser mode — the assistant config travels
to the page, the browser starts the call via @vapi-ai/web, audio is
played + captured via WebRTC. Vapi posts call/transcript events to
/api/vapi/webhook so the dashboard can render the transcript live.

In production, swap `web_call_config()` for a server-side POST to
Vapi's /call endpoint with a customer phone number, and the same
assistant config places a real outbound call over telephony.
"""
from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from .agents import Agent
from .slots import free_slots
from .leads import Lead


def public_key() -> Optional[str]:
    """Browser-safe Vapi key used by @vapi-ai/web."""
    return os.environ.get("VAPI_PUBLIC_KEY") or None


def server_key() -> Optional[str]:
    return os.environ.get("VAPI_API_KEY") or None


def is_configured() -> bool:
    return bool(public_key())


def _slot_context() -> str:
    """Tell the agent which slots they can offer THIS call.

    The fee/booking conversation feels real when the agent quotes
    actual technician + time-window options instead of inventing them.
    """
    free = free_slots()[:6]
    if not free:
        return "No technician slots are currently free — apologize and offer to call back when one opens."
    lines = []
    for s in free:
        lines.append(f"  • {s.technician} — {s.day_label}, {s.window}")
    return ("Live technician availability (offer these and only these):\n"
            + "\n".join(lines))


def _lead_context(lead: Lead) -> str:
    lines = [f"Lead source: {lead.source}",
             f"Customer: {lead.display_name()} · phone {lead.phone or '(none)'}",
             f"City: {lead.city}",
             f"Form text: {lead.appliance_hint}"]
    if lead.language_hint:
        lines.append(f"Language hint: {lead.language_hint}")
    return "\n".join(lines)


def web_call_config(agent: Agent, lead: Optional[Lead] = None) -> dict[str, Any]:
    """Build the transient Vapi assistant config the browser will pass to vapi.start().

    Returns the assistant object inline — no pre-creation needed. Tone +
    voice + LLM + transcriber + first line + slot context all bundled.
    """
    pieces: list[str] = []
    if lead:
        pieces.append(_lead_context(lead))
    pieces.append(_slot_context())
    ctx = "\n\n".join(pieces)
    return agent.vapi_assistant(lead_context=ctx)


# ── Webhook event normalization ────────────────────────────────────────────
#
# Vapi posts events like:
#   {"message": {"type": "transcript", "role": "user", "transcript": "...", ...},
#    "call": {...}}
#   {"message": {"type": "status-update", "status": "in-progress", ...}}
#   {"message": {"type": "end-of-call-report", "summary": "...", "transcript": "..."}}
#
# We extract the bits the dashboard cares about: role+text for transcript,
# status changes, end-of-call outcome.

def parse_webhook(payload: dict) -> dict[str, Any]:
    msg = (payload.get("message") or payload) if isinstance(payload, dict) else {}
    typ = msg.get("type", "")
    if typ == "transcript":
        return {
            "kind": "transcript",
            "role": msg.get("role", "assistant"),
            "text": (msg.get("transcript") or msg.get("text") or "").strip(),
            "vapi_call_id": (payload.get("call") or {}).get("id"),
        }
    if typ in ("status-update", "call-start", "call-end"):
        st = msg.get("status") or ("ended" if typ == "call-end" else "in_progress")
        return {
            "kind": "status",
            "status": _normalize_status(st),
            "vapi_call_id": (payload.get("call") or {}).get("id"),
        }
    if typ == "end-of-call-report":
        return {
            "kind": "report",
            "transcript": msg.get("transcript", ""),
            "summary": msg.get("summary", ""),
            "ended_reason": msg.get("endedReason", ""),
            "duration": msg.get("durationSeconds"),
            "vapi_call_id": (payload.get("call") or {}).get("id"),
        }
    return {"kind": "unknown", "raw_type": typ}


def _normalize_status(s: str) -> str:
    s = (s or "").lower().replace("_", "-")
    return {
        "in-progress": "in_progress",
        "ringing": "ringing",
        "queued": "ringing",
        "forwarding": "ringing",
        "ended": "ended",
    }.get(s, s or "in_progress")


# ── Optional: real outbound phone call (milestone 1, kept here so the swap
#    from web-mode is one function away).

def place_outbound_call(agent: Agent, lead: Lead,
                        phone_number_id: Optional[str] = None) -> dict[str, Any]:
    """Place a REAL outbound phone call through Vapi (not used in demo).

    Demo uses web calls; this stays here so production wiring is a
    one-line swap. Requires VAPI_API_KEY + a Vapi phone-number ID.
    """
    key = server_key()
    if not key:
        return {"ok": False, "error": "VAPI_API_KEY not set"}
    if not lead.phone:
        return {"ok": False, "error": "lead has no phone"}
    body = {
        "assistant": web_call_config(agent, lead),
        "customer": {"number": lead.phone, "name": lead.display_name()},
        **({"phoneNumberId": phone_number_id} if phone_number_id else {}),
    }
    try:
        r = httpx.post("https://api.vapi.ai/call",
                       json=body, timeout=12,
                       headers={"Authorization": f"Bearer {key}"})
        return {"ok": r.is_success, "status": r.status_code, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
