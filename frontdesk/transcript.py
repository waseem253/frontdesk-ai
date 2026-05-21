"""Transcript → Booking field extraction.

Vapi runs the conversation; when the call ends it (or the browser bridge)
hands us the full transcript. We pass the transcript to Claude with the
exact field schema and a JSON-only output contract, then either save
a confirmed Booking or log an escalation.

No deterministic fallback for this step — without an Anthropic key the
parser returns `None` and the call ends without a booking record. The
Vapi conversation itself is unaffected; this only governs what lands
in the bookings log.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from .agents import REQUIRED_FIELDS

_SCHEMA_KEYS = [k for k, _ in REQUIRED_FIELDS]


def parse_transcript(transcript_text: str) -> Optional[dict]:
    """Returns a dict with the 10 fields + escalation hint, or None on failure."""
    if not transcript_text or not transcript_text.strip():
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    field_list = "\n".join(f"  - {k}: {label}" for k, label in REQUIRED_FIELDS)
    system = f"""You are extracting structured fields from a recorded phone-call
transcript between an AI receptionist for Safro Solutions Appliance Repair
and a customer. Return ONLY a single JSON object, no prose, no markdown
fences. Schema:

{{
  "fields": {{
{field_list}
  }},
  "escalation": null | "sealed_system" | "refund" | "warranty" | "angry" | "out_of_area",
  "booked": true | false,
  "slot_key": ""        // e.g. "Mike|Tomorrow|3:00 PM - 5:00 PM" if the agent confirmed a specific tech+slot, else ""
}}

Rules:
- `fee_agreed` is a boolean: true ONLY if the customer clearly agreed to the diagnostic fee. Hesitation is false.
- `booked` is true ONLY when every required field is filled AND fee_agreed is true AND no escalation.
- Be conservative with `escalation` — only set it when the agent explicitly transferred or refused the booking for that reason.
- Empty string for any field you can't confidently extract."""

    try:
        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=600,
            system=system,
            messages=[{"role": "user",
                       "content": "Transcript:\n\n" + transcript_text}],
        )
        text = "".join(b.text for b in r.content if b.type == "text").strip()
    except Exception as e:
        print(f"[transcript] anthropic error: {e!r}")
        return None
    return _parse_json(text)


_JSON_RE = re.compile(r"\{.*\}", re.S)


def _parse_json(text: str) -> Optional[dict]:
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    m = _JSON_RE.search(cleaned)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def transcript_text_of(transcript: list[dict]) -> str:
    """Flatten our CallRecord.transcript ({role, text, at}) into a readable
    Agent: / Customer: dialog."""
    lines = []
    for chunk in transcript or []:
        if not chunk:
            continue
        role = chunk.get("role", "assistant")
        speaker = "Customer" if role == "user" else "Agent"
        text = (chunk.get("text") or "").strip()
        if text:
            lines.append(f"{speaker}: {text}")
    return "\n".join(lines)
