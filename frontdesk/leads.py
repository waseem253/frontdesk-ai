"""Lead source schemas + sample leads.

Yelp and Thumbtack send a webhook the moment a customer submits a
request. We model the exact payload shape they emit (loosely — both
platforms have their own quirks), then ship a small library of sample
leads the UI can fire with one click for the loom demo.

Sample leads cover the full matrix Maya needs to see:
  • Tony books a happy English lead (within hours)
  • Sofia handles a Spanish lead (auto language switch)
  • An out-of-hours lead is queued (no call placed)
  • An out-of-service-area lead is declined politely
  • A lead with no phone number is texted instead of called
  • A second lead arriving while Tony is busy rolls over to Sofia
"""
from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Lead:
    """Normalized lead — matches Yelp & Thumbtack semantics."""
    source: str                     # "yelp" | "thumbtack" | "web"
    external_id: str                # platform-side ID
    received_at: float              # epoch seconds
    customer_first_name: str
    customer_last_name: str
    phone: Optional[str]            # E.164 if known; None forces SMS path
    city: str                       # used for service-area gate
    appliance_hint: str             # short form text from the form
    language_hint: str = "en"       # "en" | "es"
    consent_call: bool = True       # opt-in flag from form
    raw_payload: dict = field(default_factory=dict)

    def display_name(self) -> str:
        return f"{self.customer_first_name} {self.customer_last_name}".strip()


# ── Yelp-shape payload (sample) ─────────────────────────────────────────────
# Yelp Lead Webhooks send a JSON like this when a consumer submits a quote
# request. We translate it into our normalized Lead.

def from_yelp_webhook(payload: dict) -> Lead:
    consumer = payload.get("consumer", {})
    return Lead(
        source="yelp",
        external_id=str(payload.get("project_id") or payload.get("id") or ""),
        received_at=dt.datetime.now().timestamp(),
        customer_first_name=str(consumer.get("first_name", "")).strip(),
        customer_last_name=str(consumer.get("last_name", "")).strip(),
        phone=consumer.get("phone"),
        city=str(consumer.get("city", "")).strip(),
        appliance_hint=str(payload.get("project_text", "")).strip(),
        language_hint=str(payload.get("language", "en")).lower(),
        consent_call=bool(consumer.get("opt_in_call", True)),
        raw_payload=payload,
    )


def from_thumbtack_webhook(payload: dict) -> Lead:
    req = payload.get("request", {})
    return Lead(
        source="thumbtack",
        external_id=str(payload.get("requestPk") or payload.get("id") or ""),
        received_at=dt.datetime.now().timestamp(),
        customer_first_name=str(req.get("firstName", "")).strip(),
        customer_last_name=str(req.get("lastName", "")).strip(),
        phone=req.get("phoneNumber"),
        city=str(req.get("city", "")).strip(),
        appliance_hint=str(req.get("description", "")).strip(),
        language_hint=str(req.get("language", "en")).lower(),
        consent_call=bool(req.get("phoneConsent", True)),
        raw_payload=payload,
    )


# ── Sample leads for the demo (one-click fire) ──────────────────────────────

def _yelp(eid: str, fn: str, ln: str, phone: Optional[str], city: str,
          appliance: str, lang: str = "en", consent: bool = True) -> dict:
    return {
        "project_id": eid,
        "language": lang,
        "consumer": {
            "first_name": fn, "last_name": ln, "phone": phone,
            "city": city, "opt_in_call": consent,
        },
        "project_text": appliance,
        "business": {"name": "Safro Solutions Appliance Repair"},
    }


SAMPLE_LEADS: list[dict] = [
    {
        "key": "yelp-happy",
        "label": "Yelp lead · Marcus Lee — dryer not heating (English)",
        "summary": "Standard happy path. Tony picks up, books, fee accepted.",
        "tag": "booking",
        "payload": _yelp(
            "yelp_lead_001", "Marcus", "Lee", "+15105550119", "Burbank",
            "GE dryer not heating, drum spins fine", "en",
        ),
    },
    {
        "key": "yelp-spanish",
        "label": "Yelp lead · Lucia Ramírez — fridge cooling problem (Spanish)",
        "summary": "Caller speaks Spanish. Routing prefers Sofia. Sofia opens in ES, switches if needed.",
        "tag": "spanish",
        "payload": _yelp(
            "yelp_lead_002", "Lucía", "Ramírez", "+18185550144", "Van Nuys",
            "Refrigerador Whirlpool — el congelador no enfría", "es",
        ),
    },
    {
        "key": "thumbtack-busy",
        "label": "Thumbtack · Diana Park — Tony busy, rolls to Sofia",
        "summary": "Lands while Tony is on another call. Router rolls over to Sofia per overflow chain.",
        "tag": "rollover",
        "force_busy": ["tony"],         # simulate Tony already on a call
        "payload": _yelp(
            "thumbtack_lead_001", "Diana", "Park", "+13105550199", "Sherman Oaks",
            "Dishwasher leaking under the door", "en",
        ),
    },
    {
        "key": "yelp-after-hours",
        "label": "Yelp lead at 2:14 AM — outside business hours",
        "summary": "Router refuses to call; queues for 7:00 AM. Telegram alert fires immediately.",
        "tag": "queued",
        "force_hour": 2,                # pretend it's 2:14 AM local
        "force_minute": 14,
        "payload": _yelp(
            "yelp_lead_003", "Jenna", "Walsh", "+14155550133", "Pasadena",
            "Oven not heating, error F2", "en",
        ),
    },
    {
        "key": "yelp-out-of-area",
        "label": "Yelp lead from Anchorage AK — out of service area",
        "summary": "Service-area gate rejects. Lead logged, dispatcher notified.",
        "tag": "rejected",
        "payload": _yelp(
            "yelp_lead_004", "Tom", "Bryant", "+19075550177", "Anchorage",
            "AC blowing warm air, no cool", "en",
        ),
    },
    {
        "key": "yelp-no-phone",
        "label": "Yelp lead with no phone — sends SMS / Yelp DM instead",
        "summary": "Without a phone we can't call — system queues a text follow-up on the platform.",
        "tag": "text",
        "payload": _yelp(
            "yelp_lead_005", "Priya", "Shah", None, "Studio City",
            "Washer making loud banging noise", "en",
        ),
    },
]


def sample_by_key(key: str) -> Optional[dict]:
    for s in SAMPLE_LEADS:
        if s["key"] == key:
            return s
    return None
