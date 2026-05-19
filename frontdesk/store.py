"""In-memory state: per-caller booking sessions, confirmed bookings, and
the Telegram chats that have /start-ed the bot (so confirmations can be
delivered to a real chat). Production swaps this for Postgres/Redis +
Google Calendar behind the same shape — one-file change.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class Session:
    caller: str
    data: dict = field(default_factory=dict)  # name, service, phone, slot
    asked: str = ""                            # field currently being collected
    offered: list[str] = field(default_factory=list)
    history: list[dict] = field(default_factory=list)


@dataclass
class Booking:
    id: str
    caller: str
    name: str
    service: str
    phone: str
    slot: str
    channel: str          # inbound | outbound
    created_at: float = field(default_factory=time.time)


_sessions: dict[str, Session] = {}
_bookings: list[Booking] = []
_tg_chats: set[int] = set()       # chat_ids that messaged the bot


def session(caller: str) -> Session:
    if caller not in _sessions:
        _sessions[caller] = Session(caller=caller)
    return _sessions[caller]


def reset_session(caller: str) -> None:
    _sessions.pop(caller, None)


def add_booking(b: Booking) -> None:
    _bookings.append(b)


def bookings() -> list[Booking]:
    return list(reversed(_bookings))


def register_chat(chat_id: int) -> None:
    _tg_chats.add(chat_id)


def telegram_chats() -> list[int]:
    return list(_tg_chats)
