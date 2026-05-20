"""In-memory state: per-caller booking sessions, confirmed bookings, and
the Telegram chats that have /start-ed the bot (so confirmations can be
delivered to a real chat). Production swaps this for Postgres/Redis +
Google Calendar behind the same shape — one-file change.

Schema follows Maya's spec for Safro Solutions Appliance Repair: every
booking carries the full intake (address, appliance, brand, model,
problem, window, access notes, fee agreement) — not just name/service/
slot like a generic receptionist.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Session:
    caller: str
    agent: str = "amanda"                       # "amanda" | "tony"
    data: dict = field(default_factory=dict)    # name, phone, address, ...
    asked: str = ""                              # field last asked (fallback only)
    history: list[dict] = field(default_factory=list)
    escalation: str | None = None                # ESCALATION_REASONS key
    greeted: bool = False


@dataclass
class Booking:
    id: str
    caller: str
    agent: str                # "amanda" | "tony"
    channel: str              # "inbound" | "outbound"
    name: str
    phone: str
    address: str
    appliance: str
    brand: str
    model: str
    problem: str
    window: str
    access: str
    fee_agreed: bool
    created_at: float = field(default_factory=time.time)


_sessions: dict[str, Session] = {}
_bookings: list[Booking] = []
_tg_chats: set[int] = set()
_escalations: list[dict] = []


def session(caller: str, agent: str = "amanda") -> Session:
    s = _sessions.get(caller)
    if s is None or s.agent != agent:
        s = Session(caller=caller, agent=agent)
        _sessions[caller] = s
    return s


def reset_session(caller: str) -> None:
    _sessions.pop(caller, None)


def add_booking(b: Booking) -> None:
    _bookings.append(b)


def bookings() -> list[Booking]:
    return list(reversed(_bookings))


def log_escalation(caller: str, agent: str, reason: str, summary: str) -> None:
    _escalations.append({
        "caller": caller, "agent": agent, "reason": reason,
        "summary": summary, "at": time.time(),
    })


def escalations() -> list[dict]:
    return list(reversed(_escalations))


def register_chat(chat_id: int) -> None:
    _tg_chats.add(chat_id)


def telegram_chats() -> list[int]:
    return list(_tg_chats)
