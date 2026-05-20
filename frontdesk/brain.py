"""LLM-driven conversation for Amanda + Tony.

Every turn we send the agent's system prompt + the running transcript to
Anthropic and ask for a single JSON object: {reply, fields, escalate,
ready_to_book}. We parse it, merge fields into the session, flag
escalation, and tell the pipeline whether to book.

If `ANTHROPIC_API_KEY` is missing or a call fails, we fall back to a
deterministic walker so the demo still completes — no silent dead-ends.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

from .agents import AMANDA, ESCALATION_REASONS, FEE_PITCH, REQUIRED_FIELDS, Agent
from .store import Session

_FIELD_KEYS = {k for k, _ in REQUIRED_FIELDS}


def advance(sess: Session, message: str, agent: Agent) -> dict:
    """Run one turn. Returns {reply, ready_to_book, escalate}.

    Mutates sess: appends to history, merges extracted fields, sets
    escalation. The pipeline layer turns ready_to_book into a real
    booking + Telegram/SMS broadcast.
    """
    sess.history.append({"role": "user", "text": message})
    parsed = _call_llm(sess, agent) or _fallback_turn(sess, message, agent)

    _merge_fields(sess, parsed.get("fields") or {})

    escalate = parsed.get("escalate")
    if escalate and escalate in ESCALATION_REASONS:
        sess.escalation = escalate

    reply = (parsed.get("reply") or "").strip() or "Sorry — could you say that again?"
    sess.history.append({"role": "assistant", "text": reply})

    ready = bool(parsed.get("ready_to_book")) and not sess.escalation
    if ready:
        ready = all(sess.data.get(k) for k, _ in REQUIRED_FIELDS)

    return {"reply": reply, "ready_to_book": ready, "escalate": sess.escalation}


# ---------------------------------------------------------------------------
# Anthropic call
# ---------------------------------------------------------------------------

def _call_llm(sess: Session, agent: Agent) -> dict | None:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    messages = _messages_from_history(sess)
    if not messages:
        return None

    try:
        c = anthropic.Anthropic(api_key=key)
        r = c.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=400,
            system=agent.system_prompt,
            messages=messages,
        )
        text = "".join(b.text for b in r.content if b.type == "text").strip()
    except Exception as e:
        print(f"[brain] anthropic error: {e!r}")
        return None

    return _parse_json(text)


def _messages_from_history(sess: Session) -> list[dict]:
    """Convert internal history to Anthropic's messages format.

    Anthropic requires alternating user/assistant turns starting with
    user. Our history records every turn; we collapse consecutive
    same-role messages and ensure the sequence starts with user.
    """
    out: list[dict] = []
    for h in sess.history:
        role = "assistant" if h["role"] == "assistant" else "user"
        text = h["text"]
        if out and out[-1]["role"] == role:
            out[-1]["content"] += "\n" + text
        else:
            out.append({"role": role, "content": text})
    # Anthropic disallows a leading assistant turn.
    while out and out[0]["role"] != "user":
        out.pop(0)
    return out


_JSON_RE = re.compile(r"\{.*\}", re.S)


def _parse_json(text: str) -> dict | None:
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


# ---------------------------------------------------------------------------
# Field merging
# ---------------------------------------------------------------------------

def _merge_fields(sess: Session, fields: dict[str, Any]) -> None:
    for k, v in fields.items():
        if k not in _FIELD_KEYS:
            continue
        if k == "fee_agreed":
            sess.data["fee_agreed"] = bool(v)
            continue
        if v is None:
            continue
        s = str(v).strip()
        if s:
            sess.data[k] = s


# ---------------------------------------------------------------------------
# Deterministic fallback — runs without an API key so the demo can't dead-end
# ---------------------------------------------------------------------------

_FALLBACK_QUESTIONS = {
    "name":      "May I take your name, please?",
    "phone":     "Thanks. What's the best mobile number to reach you on?",
    "address":   "Got it. What's the full address with ZIP code?",
    "appliance": "Which appliance is giving you trouble — refrigerator, washer, dryer, dishwasher, oven?",
    "brand":     "Got it. What brand is it — Whirlpool, GE, Samsung, LG?",
    "model":     "Do you have the model number handy? It's fine if not.",
    "problem":   "And what's it doing — or not doing?",
    "window":    "When works best for the visit — a morning or afternoon, weekday or weekend?",
    "access":    "Any access notes I should pass to the technician — gate code, pets, parking?",
    "fee_agreed": (
        f"One thing before I lock it in — {FEE_PITCH} "
        "Shall I go ahead and book the visit?"
    ),
}

_FEE_PUSHBACK_RE = re.compile(
    r"\b(too much|expensive|free|why.*fee|hesitat|not sure|think about|don'?t want to pay)\b",
    re.I,
)
_FEE_AGREE_RE = re.compile(
    r"\b(yes|yeah|sure|ok(ay)?|that'?s fine|go ahead|book it|sounds good|alright)\b",
    re.I,
)
_ESCALATE_PATTERNS = [
    ("sealed_system", re.compile(r"\b(freon|refrigerant|sealed system|compressor leak)\b", re.I)),
    ("refund",        re.compile(r"\brefund\b", re.I)),
    ("warranty",      re.compile(r"\bwarrant(y|ies)\b", re.I)),
    ("angry",         re.compile(r"\b(furious|ridiculous|scam|terrible|awful|fuck|damn|stupid)\b", re.I)),
    ("out_of_area",   re.compile(r"\b(out of state|alaska|hawaii|canada|mexico|two hours away)\b", re.I)),
]


def _fallback_turn(sess: Session, message: str, agent: Agent) -> dict:
    msg = message.strip()
    for reason, pat in _ESCALATE_PATTERNS:
        if pat.search(msg):
            return {
                "reply": _escalation_reply(reason, agent),
                "fields": {},
                "escalate": reason,
                "ready_to_book": False,
            }

    asked = sess.asked
    fields: dict[str, Any] = {}

    if asked == "fee_agreed":
        if _FEE_AGREE_RE.search(msg) and not _FEE_PUSHBACK_RE.search(msg):
            fields["fee_agreed"] = True
        elif _FEE_PUSHBACK_RE.search(msg):
            sess.asked = "fee_agreed"
            return {
                "reply": (
                    "I hear you — and I want to be straight with you. "
                    f"{FEE_PITCH} Want me to go ahead and reserve it?"
                ),
                "fields": {},
                "escalate": None,
                "ready_to_book": False,
            }
    elif asked and asked in _FIELD_KEYS:
        fields[asked] = msg

    next_field = _next_missing(sess, fields)
    if next_field is None and fields.get("fee_agreed") is True:
        return {
            "reply": "Perfect — you're all booked. You'll get a confirmation by text shortly.",
            "fields": fields,
            "escalate": None,
            "ready_to_book": True,
        }
    if next_field is None:
        next_field = "fee_agreed"

    sess.asked = next_field
    return {
        "reply": _FALLBACK_QUESTIONS[next_field],
        "fields": fields,
        "escalate": None,
        "ready_to_book": False,
    }


def _next_missing(sess: Session, just_set: dict[str, Any]) -> str | None:
    merged = {**sess.data, **just_set}
    for k, _ in REQUIRED_FIELDS:
        if k == "fee_agreed":
            if not merged.get("fee_agreed"):
                return "fee_agreed"
            continue
        if not merged.get(k):
            return k
    return None


def _escalation_reply(reason: str, agent: Agent) -> str:
    label = ESCALATION_REASONS[reason].lower()
    return (
        f"That falls under {label} — let me get one of our dispatchers on this "
        "with you. Please hold a moment."
    )


# ---------------------------------------------------------------------------
# Public greeting — first message the agent says when the call connects.
# ---------------------------------------------------------------------------

def greeting(agent: Agent = AMANDA) -> str:
    return agent.opening_line
