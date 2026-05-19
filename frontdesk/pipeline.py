"""Ties the conversation to the integrations: when a booking completes,
create it, deliver a Telegram confirmation (real), send the SMS
(dry-run), and log it — the inbound 'call → booked → logged' path.
"""
from __future__ import annotations

import time

from .brain import advance, polish
from .sms import send_sms
from .store import Booking, add_booking, reset_session, session
from .telegram import broadcast_booking


def _summary(b: Booking) -> str:
    return (f"New booking ({b.channel})\n"
            f"{b.name} — {b.service}\n"
            f"When: {b.slot}\nPhone: {b.phone}\nRef: {b.id}")


def handle_turn(caller: str, message: str) -> dict:
    sess = session(caller)
    reply, done = advance(sess, message)
    result: dict = {"reply": polish(reply), "booked": False}

    if done:
        d = sess.data
        b = Booking(
            id="bk_" + format(int(time.time() * 1000) % 10_000_000, "x"),
            caller=caller,
            name=d.get("name", "Guest"),
            service=d.get("service", "appointment"),
            phone=d.get("phone", ""),
            slot=d.get("slot", ""),
            channel="inbound",
        )
        add_booking(b)
        summary = _summary(b)
        tg = broadcast_booking(summary)
        sms = send_sms(b.phone, f"Confirmed: {b.slot}, {b.service}. Ref {b.id}")
        reset_session(caller)
        result.update(booked=True, booking=b.__dict__,
                      telegram=tg, sms=sms)
    return result


def outbound_call(lead_name: str, phone: str, service: str) -> dict:
    """Scope 2: a new lead triggers an automated outbound call. Demo
    fast-paths to a booking + the same Telegram/SMS/log path; production
    adds the answer/no-answer retry ladder (max 3 over ~3 days)."""
    b = Booking(
        id="bk_" + format(int(time.time() * 1000) % 10_000_000, "x"),
        caller=phone, name=lead_name, service=service,
        phone=phone, slot="Tomorrow 11:15", channel="outbound",
    )
    add_booking(b)
    summary = _summary(b) + "\n(outbound auto-call → booked)"
    tg = broadcast_booking(summary)
    sms = send_sms(phone, f"We booked you {b.slot} for {service}. Ref {b.id}")
    return {"booking": b.__dict__, "telegram": tg, "sms": sms,
            "note": "Prod: 3 smart retries over ~3 days if unanswered."}
