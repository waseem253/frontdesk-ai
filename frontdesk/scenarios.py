"""Pre-scripted demo callers — the UI plays these line-by-line.

Each scenario seeds a fresh session for a chosen agent and then sends a
sequence of caller lines through the same /api/call/turn endpoint, so
what Maya sees is the real conversation engine handling realistic input
— not a recording. The five scenarios cover Maya's explicit asks:
happy booking, diagnostic-fee objection, sealed-system escalation,
out-of-service-area escalation, and an angry customer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    tag: str               # one-word badge: "booking" | "objection" | "escalate"
    agent: str             # "amanda" | "tony"
    summary: str
    lines: list[str] = field(default_factory=list)
    seed: dict = field(default_factory=dict)   # pre-filled fields (Tony only)


SCENARIOS: list[Scenario] = [
    Scenario(
        key="happy",
        title="Happy booking — fridge not cooling",
        tag="booking",
        agent="amanda",
        summary="Standard intake: Amanda collects the full booking and confirms the diagnostic fee on the first ask.",
        lines=[
            "Hi, my fridge stopped cooling last night and the freezer is dripping.",
            "Sarah Khan.",
            "415 555 0144.",
            "1820 Oak Street, apartment 4B, San Jose, 95126.",
            "It's a refrigerator.",
            "Whirlpool.",
            "I think it's WRF555SDFZ, give me a sec — yeah, WRF555SDFZ.",
            "The fresh-food side is at room temp and the freezer is barely cold. Started yesterday evening.",
            "Tomorrow afternoon would be perfect.",
            "Gate code 4412, the dog is friendly, park in the visitor spot by the mailboxes.",
            "Yes, that's fine, please go ahead and book it.",
        ],
    ),

    Scenario(
        key="fee-objection",
        title="Diagnostic-fee objection — convert with the value pitch",
        tag="objection",
        agent="amanda",
        summary="Caller pushes back on the fee. Amanda lands the value pitch (travel, expertise, time slot reserved) and earns the booking.",
        lines=[
            "My washer is leaking from the bottom every cycle.",
            "Daniel Park.",
            "415 555 0188.",
            "227 Lincoln Avenue, Sunnyvale, 94086.",
            "Washing machine, Samsung, model WF45T6000AW.",
            "Water pools under it after every cycle, mostly the front side.",
            "Saturday morning if possible.",
            "Front gate is open, no pets.",
            "Wait — $89 just for someone to come look? That feels steep, I'm not sure I want to pay that.",
            "Hm, but what if it's just a hose or something simple — am I still paying $89?",
            "Okay, that actually makes sense when you put it like that. Go ahead and book it.",
        ],
    ),

    Scenario(
        key="sealed-system",
        title="Sealed-system / Freon — must escalate",
        tag="escalate",
        agent="amanda",
        summary="Caller mentions Freon / refrigerant. Amanda stops collecting and transfers to a dispatcher.",
        lines=[
            "Hi, my AC has been blowing warm air for about a week.",
            "Lisa Torres, 408 555 0102.",
            "I think it needs a freon recharge — the refrigerant must be low.",
        ],
    ),

    Scenario(
        key="out-of-area",
        title="Outside service area — polite decline + escalate",
        tag="escalate",
        agent="amanda",
        summary="Caller is in another state. Amanda confirms it's out of area and routes to a dispatcher who can refer them.",
        lines=[
            "Hi, my oven door won't latch and it shows an error code.",
            "I'm in Anchorage Alaska — do you cover this far out of state?",
        ],
    ),

    Scenario(
        key="angry",
        title="Angry caller — de-escalate, then transfer",
        tag="escalate",
        agent="amanda",
        summary="Caller is furious about a previous visit. Amanda de-escalates once and routes to a human supervisor.",
        lines=[
            "This is ridiculous — your technician came out last week and the dishwasher is broken again.",
            "I want a refund, your service was terrible and a total scam.",
        ],
    ),

    Scenario(
        key="tony-outbound",
        title="Tony — outbound Yelp lead callback",
        tag="booking",
        agent="tony",
        summary="A fresh Yelp lead just submitted a form. Tony calls back immediately, confirms the request, and books.",
        seed={
            "name": "Marcus Lee",
            "phone": "+1 510 555 0119",
            "problem": "GE dryer not heating, drum spins fine",
        },
        lines=[
            "Yeah hi, that's me — I just submitted the form.",
            "Address is 412 Pine Street, Oakland, 94607.",
            "It's a GE dryer, model GTD45EASJWS.",
            "Drum spins, clothes come out wet, no heat at all.",
            "Tomorrow morning would be great.",
            "Side gate by the garage, code is 8821, no pets.",
            "Yeah that sounds fair — go ahead and book it.",
        ],
    ),
]
