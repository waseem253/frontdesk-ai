"""Technician schedule — mock 'Google Sheet' for the demo.

Maya uses Google Sheets today (not Google Calendar yet). The shape here
mirrors a Sheet row: technician name, date, start, end, booked-by.
We expose simple read + book operations so the ops dashboard can show
slots filling in real time during a call. Production swaps this for
gspread + a real Sheet ID (or KickStarter CRM + Google Calendar) with
no API changes above.
"""
from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Slot:
    technician: str            # "Mike", "Carlos", "Dave"
    day_label: str             # "Tomorrow", "Thursday", "Friday"
    window: str                # "9:00 AM - 11:00 AM"
    booked_by: Optional[str] = None    # booking id when taken
    held_for: Optional[str] = None     # caller id holding it mid-call

    @property
    def free(self) -> bool:
        return self.booked_by is None and self.held_for is None

    def key(self) -> str:
        return f"{self.technician}|{self.day_label}|{self.window}"


_lock = threading.Lock()


def _seed() -> list[Slot]:
    """Three technicians × three slots/day × three days = 27 slots.

    One is pre-booked so the demo shows partial availability honestly:
    'Mike has Tuesday 9 AM taken — offering Carlos at 9 AM, or Mike at 11.'
    """
    techs = ["Mike", "Carlos", "Dave"]
    days = [("Tomorrow", 1), ("Day after", 2), ("In 3 days", 3)]
    windows = ["9:00 AM - 11:00 AM", "12:00 PM - 2:00 PM", "3:00 PM - 5:00 PM"]
    out: list[Slot] = []
    for tech in techs:
        for day_label, _ in days:
            for w in windows:
                out.append(Slot(technician=tech, day_label=day_label, window=w))
    # Pre-book one so the demo isn't deceptively empty.
    out[0].booked_by = "seed_bk_existing"      # Mike · Tomorrow · 9-11 AM
    out[1].booked_by = "seed_bk_existing"      # Mike · Tomorrow · 12-2 PM
    return out


_slots: list[Slot] = _seed()


def all_slots() -> list[Slot]:
    with _lock:
        return list(_slots)


def free_slots() -> list[Slot]:
    with _lock:
        return [s for s in _slots if s.free]


def first_free() -> Optional[Slot]:
    with _lock:
        for s in _slots:
            if s.free:
                return s
    return None


def hold(slot_key: str, caller: str) -> bool:
    with _lock:
        for s in _slots:
            if s.key() == slot_key and s.free:
                s.held_for = caller
                return True
    return False


def release(caller: str) -> None:
    with _lock:
        for s in _slots:
            if s.held_for == caller:
                s.held_for = None


def book(slot_key: str, booking_id: str, caller: Optional[str] = None) -> bool:
    """Promote a held (or simply free) slot into a confirmed booking."""
    with _lock:
        for s in _slots:
            if s.key() == slot_key and s.booked_by is None:
                if s.held_for and caller and s.held_for != caller:
                    return False
                s.booked_by = booking_id
                s.held_for = None
                return True
    return False


def reset_demo() -> None:
    """Reset slot state — useful between demo runs."""
    global _slots
    with _lock:
        _slots = _seed()


# ── Business hours / queue policy (see scheduler.py) ───────────────────────
BUSINESS_OPEN_HOUR = 7    # 7:00 AM Pacific
BUSINESS_CLOSE_HOUR = 19  # 7:00 PM Pacific

try:
    from zoneinfo import ZoneInfo
    PACIFIC_TZ = ZoneInfo("America/Los_Angeles")
except Exception:           # zoneinfo or tz data unavailable — fall back to UTC-7
    PACIFIC_TZ = dt.timezone(dt.timedelta(hours=-7))


def now_pacific() -> dt.datetime:
    """Current wall-clock in the business's timezone (Pacific).

    Vercel runs serverless functions in UTC, so a naive datetime.now()
    is UTC — wrong for a California appliance business. Always resolve
    against America/Los_Angeles.
    """
    return dt.datetime.now(PACIFIC_TZ)


def is_within_business_hours(now: Optional[dt.datetime] = None) -> bool:
    """True if calling now is allowed. Per Maya: do NOT call outside hours."""
    now = now or now_pacific()
    return BUSINESS_OPEN_HOUR <= now.hour < BUSINESS_CLOSE_HOUR
