"""Out-of-hours queue + unanswered-call retry ladder.

Per Maya's call (5/20):
  • A lead arriving outside business hours must be QUEUED, not called.
    The scheduler fires the queue when business hours begin.
  • If a placed call is unanswered, retry after 20 min → 24 h → 72 h.
    After the 3rd failed attempt, stop (Yelp anti-spam policy).

This module is the policy + state — the actual dial is performed by
main.py / vapi_client.py.  In the demo it runs in-memory; in
production it sits behind the same shape and persists per lead.
"""
from __future__ import annotations

import datetime as dt
import threading
import time
from dataclasses import dataclass, field
from typing import Optional


# Retry ladder per Maya's spec. Demo-friendly fast values are exposed
# via env so a loom recording can show the next retry within seconds
# without waiting 20 real minutes.
RETRY_SCHEDULE_MIN = [20, 24 * 60, 72 * 60]   # minutes
MAX_ATTEMPTS = 3


@dataclass
class QueuedLead:
    lead_id: str
    lead_summary: str
    fire_at: float                    # epoch seconds
    reason: str                       # "after_hours" | "retry" | "all_busy"
    attempts: int = 0


_lock = threading.Lock()
_queue: list[QueuedLead] = []
_history: list[dict] = []           # rendered fire/skipped log for the UI


def enqueue(lead_id: str, summary: str, fire_at: float, reason: str,
            attempts: int = 0) -> QueuedLead:
    q = QueuedLead(lead_id=lead_id, lead_summary=summary,
                   fire_at=fire_at, reason=reason, attempts=attempts)
    with _lock:
        _queue.append(q)
        _queue.sort(key=lambda x: x.fire_at)
    return q


def queue_snapshot() -> list[dict]:
    with _lock:
        now = time.time()
        return [
            {
                "lead_id": q.lead_id,
                "summary": q.lead_summary,
                "reason": q.reason,
                "attempts": q.attempts,
                "fire_at": q.fire_at,
                "fire_in_seconds": max(0, q.fire_at - now),
                "fire_label": _humanize(q.fire_at - now),
            }
            for q in _queue
        ]


def history_snapshot() -> list[dict]:
    with _lock:
        return list(reversed(_history))[:25]


def record_attempt(lead_id: str, outcome: str, agent_key: str) -> None:
    """outcome: 'answered' | 'no_answer' | 'busy' | 'failed' | 'queued'."""
    with _lock:
        _history.append({
            "lead_id": lead_id, "outcome": outcome,
            "agent": agent_key, "at": time.time(),
        })


def schedule_retry(lead_id: str, summary: str, attempts_so_far: int,
                   now: Optional[dt.datetime] = None) -> Optional[QueuedLead]:
    """Place the lead back into the queue per the retry ladder.

    Returns the new queue entry, or None if we've hit MAX_ATTEMPTS and
    must stop calling (anti-spam).
    """
    if attempts_so_far >= MAX_ATTEMPTS:
        return None
    delay_min = RETRY_SCHEDULE_MIN[min(attempts_so_far, len(RETRY_SCHEDULE_MIN) - 1)]
    fire = (now or dt.datetime.now()) + dt.timedelta(minutes=delay_min)
    return enqueue(lead_id, summary, fire.timestamp(), "retry",
                    attempts=attempts_so_far + 1)


def pop_due(now_ts: Optional[float] = None) -> list[QueuedLead]:
    """Drain leads whose fire_at has passed.

    The dashboard calls this on each lead-feed poll so due retries /
    after-hours wake-ups fire visibly in the demo loop.
    """
    now_ts = now_ts if now_ts is not None else time.time()
    fired: list[QueuedLead] = []
    with _lock:
        remaining: list[QueuedLead] = []
        for q in _queue:
            if q.fire_at <= now_ts:
                fired.append(q)
            else:
                remaining.append(q)
        _queue[:] = remaining
    return fired


def reset_demo() -> None:
    with _lock:
        _queue.clear()
        _history.clear()


def _humanize(seconds: float) -> str:
    if seconds <= 0:
        return "due now"
    if seconds < 60:
        return f"in {int(seconds)}s"
    if seconds < 3600:
        return f"in {int(seconds // 60)} min"
    if seconds < 86400:
        return f"in {int(seconds // 3600)} h"
    return f"in {int(seconds // 86400)} d"
