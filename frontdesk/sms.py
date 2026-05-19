"""SMS confirmation — Twilio in production, dry-run without creds.

Isolated so the booking flow never depends on a live SMS provider; the
demo logs the message and the architecture stays identical to prod.
"""
from __future__ import annotations

import os

import httpx


def send_sms(to: str, body: str) -> str:
    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    tok = os.environ.get("TWILIO_AUTH_TOKEN")
    frm = os.environ.get("TWILIO_FROM")
    if not (sid and tok and frm):
        print(f"[sms:dry-run -> {to}] {body}")
        return "dry-run"
    try:
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
            data={"From": frm, "To": to, "Body": body},
            auth=(sid, tok),
            timeout=15,
        )
        return "sent" if r.is_success else f"err:{r.status_code}"
    except Exception:
        return "error"
