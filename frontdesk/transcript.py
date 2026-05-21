"""Transcript → Booking field extraction.

Vapi runs the conversation; when the call ends it (or the browser bridge)
hands us the full transcript. We pass the transcript to Claude with the
exact field schema and a JSON-only output contract, then either save
a confirmed Booking or log an escalation.

A booking is created whenever the REQUIRED fields are filled and the
fee was accepted. `model` and `access` are OPTIONAL — a customer who
doesn't have the model number to hand, or has nothing special about
access, must NOT block a booking.

Without an Anthropic key the parser returns None and the call ends
without a booking record. The Vapi conversation itself is unaffected.
"""
from __future__ import annotations

import json
import os
import re
from typing import Optional

from .agents import REQUIRED_FIELDS

_OPTIONAL = {"model", "access"}
_REQUIRED_FOR_BOOK = [k for k, _ in REQUIRED_FIELDS if k not in _OPTIONAL]


def parse_transcript(transcript_text: str) -> Optional[dict]:
    """Returns a dict with the 10 fields + escalation hint, or None on failure.

    Logs each step to stdout so Vercel function logs show exactly what the
    parser saw — easier to debug 'why didn't a booking save?'.
    """
    if not transcript_text or not transcript_text.strip():
        print("[transcript] empty input — skipping parse")
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("[transcript] no ANTHROPIC_API_KEY — skipping parse")
        return None
    try:
        import anthropic
    except ImportError:
        print("[transcript] anthropic package missing — skipping parse")
        return None

    field_list = "\n".join(
        f"  - {k}: {label}" + (" (OPTIONAL — empty string is fine)"
                                if k in _OPTIONAL else " (REQUIRED for a booking)")
        for k, label in REQUIRED_FIELDS
    )
    required_keys = ", ".join(_REQUIRED_FOR_BOOK)
    system = f"""You are extracting structured fields from a recorded voice
conversation between an AI receptionist for Safro Solutions Appliance Repair
and a customer. Return ONLY a single JSON object, no prose, no markdown fences.

Schema:
{{
  "fields": {{
{field_list}
  }},
  "escalation": null | "sealed_system" | "refund" | "warranty" | "angry" | "out_of_area",
  "booked": true | false,
  "slot_key": "Mike|Tomorrow|3:00 PM - 5:00 PM"
}}

Rules:
- `fee_agreed` is a boolean: true ONLY if the customer clearly agreed to the
  diagnostic fee (e.g. "yes", "go ahead and book it", "that sounds fair").
  Hesitation alone is false.
- A booking ("booked": true) requires ALL of: every REQUIRED field filled
  ({required_keys}), `fee_agreed` is true, AND no escalation.
  OPTIONAL fields (model, access) are nice-to-have — leave them as empty
  strings if the customer didn't provide them; DO NOT let a missing optional
  field flip `booked` to false.
- For `slot_key`, use the technician name + day label + time window that the
  AGENT confirmed at the end (e.g. "Mike|Tomorrow|3:00 PM - 5:00 PM"). Empty
  string only if no slot was clearly confirmed.
- Set `escalation` only if the agent explicitly said they would transfer or
  refuse the booking for that reason.
- Be generous with phonetic variants of the company name (Safro, Sephora,
  Saphro, Sapphire — same company)."""

    try:
        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=800,
            system=system,
            messages=[{"role": "user",
                       "content": "Transcript:\n\n" + transcript_text}],
        )
        text = "".join(b.text for b in r.content if b.type == "text").strip()
    except Exception as e:
        print(f"[transcript] anthropic error: {e!r}")
        return None

    parsed = _parse_json(text)
    if parsed is None:
        print(f"[transcript] JSON parse FAILED · raw: {text[:200]}…")
        return None

    # Post-hoc enforcement of the optional-vs-required rule, in case the
    # LLM forgets and downgrades a booking over an empty access notes field.
    fields = parsed.get("fields") or {}
    missing = [k for k in _REQUIRED_FOR_BOOK if not str(fields.get(k, "")).strip()
               and k != "fee_agreed"]
    fee_ok = bool(fields.get("fee_agreed", False))
    has_escalation = bool(parsed.get("escalation"))

    if parsed.get("booked") and (missing or not fee_ok or has_escalation):
        print(f"[transcript] downgrading booked=false · missing={missing} "
              f"fee_agreed={fee_ok} escalation={parsed.get('escalation')}")
        parsed["booked"] = False
    elif not parsed.get("booked") and not missing and fee_ok and not has_escalation:
        # All required filled, fee accepted, no escalation — promote.
        print(f"[transcript] promoting booked=true · LLM said false but every "
              f"required field is present and fee_agreed is true")
        parsed["booked"] = True

    print(f"[transcript] parse OK · booked={parsed.get('booked')} "
          f"fee_agreed={fee_ok} missing_required={missing} "
          f"escalation={parsed.get('escalation')} "
          f"fields_filled={[k for k,v in fields.items() if v]}")
    return parsed


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
