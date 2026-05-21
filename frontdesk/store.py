"""In-memory state for the ops dashboard.

Shape mirrors what a production DB row would look like — every entity
(agent state, lead, call, booking, escalation) is keyed and listable so
the UI can re-render the dashboard on each poll. Production swaps this
for Postgres / Redis behind the same accessors.
"""
from __future__ import annotations

import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Optional


# ─── Booking (unchanged shape — used by chat console + ops dashboard) ───

@dataclass
class Booking:
    id: str
    caller: str
    agent: str                # "amanda" | "tony" | "sofia"
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
    slot_key: str = ""
    technician: str = ""
    lead_source: str = ""
    lead_id: str = ""
    created_at: float = field(default_factory=time.time)


# ─── Session (only used by the legacy chat console at /console) ─────────

@dataclass
class Session:
    caller: str
    agent: str = "amanda"
    data: dict = field(default_factory=dict)
    asked: str = ""
    history: list[dict] = field(default_factory=list)
    escalation: Optional[str] = None
    greeted: bool = False


# ─── Agent runtime state ────────────────────────────────────────────────

@dataclass
class AgentRuntime:
    key: str                  # "amanda" | "tony" | "sofia"
    status: str = "idle"      # "idle" | "busy" | "offline"
    current_call_id: Optional[str] = None
    current_lead_id: Optional[str] = None
    calls_today: int = 0
    bookings_today: int = 0


# ─── Lead + call event records (for the dashboard live feed) ────────────

@dataclass
class LeadRecord:
    lead_id: str
    source: str
    received_at: float
    customer_name: str
    phone: Optional[str]
    city: str
    appliance_hint: str
    language: str
    consent: bool
    decision: dict = field(default_factory=dict)   # router.Decision.as_dict()
    call_id: Optional[str] = None
    queue_reason: Optional[str] = None


@dataclass
class CallRecord:
    call_id: str
    lead_id: str
    agent_key: str
    started_at: float
    status: str = "initiating"     # initiating | ringing | in_progress | ended | failed
    ended_at: Optional[float] = None
    outcome: Optional[str] = None  # answered | no_answer | busy | failed
    transcript: list[dict] = field(default_factory=list)  # {role, text, at}
    vapi_call_id: Optional[str] = None
    booking_id: Optional[str] = None
    escalation: Optional[str] = None


# ─── Backing stores ─────────────────────────────────────────────────────

_lock = threading.Lock()
_sessions: dict[str, Session] = {}
_bookings: list[Booking] = []
_tg_chats: set[int] = set()
_escalations: list[dict] = []

_agents: dict[str, AgentRuntime] = {
    "amanda": AgentRuntime(key="amanda"),
    "tony":   AgentRuntime(key="tony"),
    "sofia":  AgentRuntime(key="sofia"),
}
_leads: dict[str, LeadRecord] = {}
_lead_order: list[str] = []
_calls: dict[str, CallRecord] = {}
_call_order: list[str] = []


# ── Sessions (legacy chat console) ──

def session(caller: str, agent: str = "amanda") -> Session:
    s = _sessions.get(caller)
    if s is None or s.agent != agent:
        s = Session(caller=caller, agent=agent)
        _sessions[caller] = s
    return s


def reset_session(caller: str) -> None:
    _sessions.pop(caller, None)


# ── Bookings ──

def add_booking(b: Booking) -> None:
    _bookings.append(b)


def bookings() -> list[Booking]:
    return list(reversed(_bookings))


# ── Escalations ──

def log_escalation(caller: str, agent: str, reason: str, summary: str) -> None:
    _escalations.append({
        "caller": caller, "agent": agent, "reason": reason,
        "summary": summary, "at": time.time(),
    })


def escalations() -> list[dict]:
    return list(reversed(_escalations))


# ── Telegram chats ──

def register_chat(chat_id: int) -> None:
    _tg_chats.add(chat_id)


def telegram_chats() -> list[int]:
    return list(_tg_chats)


# ── Agent runtime state ──

def agent_status_snapshot() -> dict[str, dict]:
    with _lock:
        return {k: asdict(a) for k, a in _agents.items()}


def set_agent_status(key: str, status: str, call_id: Optional[str] = None,
                     lead_id: Optional[str] = None) -> None:
    with _lock:
        a = _agents.get(key)
        if not a:
            return
        a.status = status
        a.current_call_id = call_id
        a.current_lead_id = lead_id


def bump_agent_counts(key: str, booked: bool = False) -> None:
    with _lock:
        a = _agents.get(key)
        if not a:
            return
        a.calls_today += 1
        if booked:
            a.bookings_today += 1


# ── Leads ──

def add_lead(rec: LeadRecord) -> None:
    with _lock:
        _leads[rec.lead_id] = rec
        if rec.lead_id not in _lead_order:
            _lead_order.append(rec.lead_id)


def get_lead(lead_id: str) -> Optional[LeadRecord]:
    return _leads.get(lead_id)


def leads_snapshot(limit: int = 20) -> list[dict]:
    with _lock:
        ids = list(reversed(_lead_order))[:limit]
        return [asdict(_leads[i]) for i in ids if i in _leads]


def update_lead_call(lead_id: str, call_id: str) -> None:
    with _lock:
        rec = _leads.get(lead_id)
        if rec:
            rec.call_id = call_id


# ── Calls ──

def add_call(rec: CallRecord) -> None:
    with _lock:
        _calls[rec.call_id] = rec
        if rec.call_id not in _call_order:
            _call_order.append(rec.call_id)


def get_call(call_id: str) -> Optional[CallRecord]:
    return _calls.get(call_id)


def set_call_status(call_id: str, status: str,
                    outcome: Optional[str] = None,
                    vapi_call_id: Optional[str] = None) -> None:
    with _lock:
        c = _calls.get(call_id)
        if not c:
            return
        c.status = status
        if status == "ended" and not c.ended_at:
            c.ended_at = time.time()
        if outcome:
            c.outcome = outcome
        if vapi_call_id:
            c.vapi_call_id = vapi_call_id


def append_transcript(call_id: str, role: str, text: str) -> None:
    with _lock:
        c = _calls.get(call_id)
        if c:
            c.transcript.append({"role": role, "text": text, "at": time.time()})


def call_snapshot(call_id: str) -> Optional[dict]:
    with _lock:
        c = _calls.get(call_id)
        return asdict(c) if c else None


def recent_calls(limit: int = 10) -> list[dict]:
    with _lock:
        ids = list(reversed(_call_order))[:limit]
        return [asdict(_calls[i]) for i in ids if i in _calls]


# ── Demo helper ──

def reset_demo() -> None:
    """Clear demo state without touching the agent registry."""
    with _lock:
        _bookings.clear()
        _escalations.clear()
        _sessions.clear()
        _leads.clear()
        _lead_order.clear()
        _calls.clear()
        _call_order.clear()
        for a in _agents.values():
            a.status = "idle"
            a.current_call_id = None
            a.current_lead_id = None
            a.calls_today = 0
            a.bookings_today = 0
