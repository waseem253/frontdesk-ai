"""The receptionist conversation.

A deterministic slot-filling flow (reliable and demo-coherent), with an
optional Anthropic pass to make the greeting/closing sound natural when
a key is present. Collects: name → what they need → phone → preferred
time, offers concrete slots, confirms, books.
"""
from __future__ import annotations

import os
import re

from .store import Session

SLOTS = ["Tomorrow 10:00", "Tomorrow 14:30", "Thursday 09:00"]

_STEPS = [
    ("name", "Thanks for calling — may I take your name?"),
    ("service", "Thank you, {name}. What can we help you with today?"),
    ("phone", "Got it. What's the best mobile number for the confirmation?"),
    ("when", "Perfect. Any preferred day or time, or shall I offer the earliest?"),
]


def _next_field(d: dict) -> tuple[str | None, str]:
    for f, prompt in _STEPS:
        if not d.get(f):
            return f, prompt
    return None, ""


def advance(sess: Session, message: str) -> tuple[str, bool]:
    """Returns (reply, booking_complete). Mutates sess.data."""
    msg = message.strip()
    sess.history.append({"role": "user", "text": msg})

    # Slot selection phase
    if sess.offered and not sess.data.get("slot"):
        chosen = _match_slot(msg, sess.offered)
        if chosen:
            sess.data["slot"] = chosen
            return (f"Booked: {chosen}, for {sess.data['name']} "
                    f"({sess.data['service']}). I'll send a confirmation now. "
                    "Anything else?"), True
        return ("Sorry, which time works — "
                + ", ".join(sess.offered) + "?"), False

    # Capture the answer to whatever we last asked
    if sess.asked:
        sess.data[sess.asked] = msg
        sess.asked = ""

    field, prompt = _next_field(sess.data)
    if field is not None:
        sess.asked = field
        return prompt.format(name=sess.data.get("name", "")), False

    # All fields collected → offer slots
    sess.offered = SLOTS
    return ("I can offer: " + ", ".join(SLOTS)
            + ". Which suits you best?"), False


def _match_slot(msg: str, offered: list[str]) -> str | None:
    low = msg.lower()
    for i, s in enumerate(offered, 1):
        if str(i) in low or s.lower() in low:
            return s
    if re.search(r"\b(first|earliest|asap|any)\b", low):
        return offered[0]
    return None


def polish(text: str) -> str:
    """Optional natural-language smoothing via Anthropic; no-op without key."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return text
    try:
        import anthropic

        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=120,
            system=("Rewrite the receptionist line to be warm, concise, "
                    "spoken-style. Keep all names, times, numbers exactly. "
                    "One or two sentences. Return only the line."),
            messages=[{"role": "user", "content": text}],
        )
        out = "".join(b.text for b in r.content if b.type == "text").strip()
        return out or text
    except Exception:
        return text
