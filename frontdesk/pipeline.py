"""Wires the conversation to the integrations.

Amanda (inbound) and Tony (outbound) share one path: turn → field
extraction → (booking | escalation) → Telegram + SMS confirmation →
in-memory log. The only difference is which agent persona is loaded and
how the call is started.
"""
from __future__ import annotations

import time

from .agents import AGENTS, AMANDA, COMPANY, DIAGNOSTIC_FEE_USD, ESCALATION_REASONS, TONY
from .brain import advance, greeting
from .sms import send_sms
from .store import (
    Booking,
    add_booking,
    log_escalation,
    reset_session,
    session,
)
from .telegram import broadcast_booking


def _new_booking(sess_caller: str, agent_key: str, d: dict) -> Booking:
    agent = AGENTS[agent_key]
    return Booking(
        id="bk_" + format(int(time.time() * 1000) % 10_000_000, "x"),
        caller=sess_caller,
        agent=agent_key,
        channel=agent.channel,
        name=str(d.get("name", "") or ""),
        phone=str(d.get("phone", "") or ""),
        address=str(d.get("address", "") or ""),
        appliance=str(d.get("appliance", "") or ""),
        brand=str(d.get("brand", "") or ""),
        model=str(d.get("model", "") or ""),
        problem=str(d.get("problem", "") or ""),
        window=str(d.get("window", "") or ""),
        access=str(d.get("access", "") or ""),
        fee_agreed=bool(d.get("fee_agreed", False)),
    )


def _booking_summary(b: Booking) -> str:
    agent_label = AGENTS.get(b.agent, AMANDA).name
    return (
        f"📞 New booking — {COMPANY}\n"
        f"Agent: {agent_label} ({b.channel})\n"
        f"Customer: {b.name}\n"
        f"Phone: {b.phone}\n"
        f"Address: {b.address}\n"
        f"Appliance: {b.appliance} · {b.brand} · model {b.model or 'n/a'}\n"
        f"Problem: {b.problem}\n"
        f"Window: {b.window}\n"
        f"Access notes: {b.access or '—'}\n"
        f"Diagnostic fee accepted: {'yes' if b.fee_agreed else 'no'}\n"
        f"Ref: {b.id}"
    )


def _escalation_summary(caller: str, agent_key: str, reason: str, data: dict) -> str:
    agent_label = AGENTS.get(agent_key, AMANDA).name
    label = ESCALATION_REASONS.get(reason, reason)
    captured = ", ".join(f"{k}={v}" for k, v in data.items() if v) or "—"
    return (
        f"⚠️  ESCALATION — {COMPANY}\n"
        f"Agent: {agent_label}\n"
        f"Reason: {label}\n"
        f"Caller: {caller}\n"
        f"Captured so far: {captured}\n"
        "→ Route to a human dispatcher."
    )


def start_call(caller: str, agent_key: str = "amanda") -> dict:
    """Open a new call. Returns the agent's first line + snapshot."""
    reset_session(caller)
    sess = session(caller, agent_key)
    sess.greeted = True
    line = greeting(AGENTS.get(agent_key, AMANDA))
    sess.history.append({"role": "assistant", "text": line})
    return _snapshot(sess, reply=line, booked=False, escalation=None)


def handle_turn(caller: str, message: str, agent_key: str = "amanda") -> dict:
    sess = session(caller, agent_key)
    agent = AGENTS.get(agent_key, AMANDA)

    if not sess.greeted:
        sess.greeted = True
        sess.history.append({"role": "assistant", "text": agent.opening_line})

    out = advance(sess, message, agent)
    reply = out["reply"]
    escalate = out["escalate"]
    ready = out["ready_to_book"]

    booked_payload = None
    if escalate:
        summary = _escalation_summary(caller, agent_key, escalate, sess.data)
        tg = broadcast_booking(summary)
        log_escalation(caller, agent_key, escalate, summary)
        return _snapshot(sess, reply=reply, booked=False, escalation=escalate,
                         telegram=tg)

    if ready:
        b = _new_booking(caller, agent_key, sess.data)
        add_booking(b)
        summary = _booking_summary(b)
        tg = broadcast_booking(summary)
        fee_line = (
            f"Diagnostic fee ${DIAGNOSTIC_FEE_USD} accepted."
            if b.fee_agreed else "Diagnostic fee pending."
        )
        sms = send_sms(
            b.phone,
            f"{COMPANY}: you're booked for {b.window}. {fee_line} Ref {b.id}.",
        )
        booked_payload = {"booking": b.__dict__, "telegram": tg, "sms": sms}

    snap = _snapshot(sess, reply=reply, booked=bool(booked_payload),
                     escalation=None)
    if booked_payload:
        snap.update(booked_payload)
        reset_session(caller)
    return snap


def trigger_outbound(name: str, phone: str, problem: str = "") -> dict:
    """Tony places a fresh outbound call to a Yelp / Thumbtack lead.

    Returns the snapshot for the UI to drive the rest of the conversation.
    Tony already knows the lead's name + phone + problem from the form
    they submitted — that's seeded into the session so he can confirm
    it instead of asking blind.
    """
    caller = phone or f"lead-{int(time.time())}"
    reset_session(caller)
    sess = session(caller, "tony")
    sess.greeted = True
    if name:
        sess.data["name"] = name
    if phone:
        sess.data["phone"] = phone
    if problem:
        sess.data["problem"] = problem
    line = TONY.opening_line
    sess.history.append({"role": "assistant", "text": line})
    snap = _snapshot(sess, reply=line, booked=False, escalation=None)
    snap["caller"] = caller
    return snap


def _snapshot(sess, reply: str, booked: bool, escalation: str | None,
              telegram: dict | None = None) -> dict:
    return {
        "reply": reply,
        "booked": booked,
        "escalation": escalation,
        "fields": dict(sess.data),
        "agent": sess.agent,
        "telegram": telegram,
    }
