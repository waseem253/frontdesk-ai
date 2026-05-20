"""FastAPI: Safro Solutions AI Receptionist & Booking demo.

Two agents (Amanda inbound, Tony outbound) live behind a single HTML
console. Telegram delivery is real when a token is set, otherwise
dry-run logged. SMS and voice telephony are dry-run in the demo and
real in production (Twilio / Vapi).
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from .agents import AGENTS, COMPANY, DIAGNOSTIC_FEE_USD, REQUIRED_FIELDS
from .pipeline import handle_turn, start_call, trigger_outbound
from .scenarios import SCENARIOS
from .store import bookings, escalations
from .telegram import handle_update, set_webhook
from .ui import INDEX_HTML

app = FastAPI(title="Safro Receptionist AI", version="2.0.0")

BOT_HANDLE = "inbound_call_bot"  # t.me/inbound_call_bot — registered Telegram bot
DEMO_PHONE = "+1 (747) 900-2649"


# ---------------------------------------------------------------------------
# Health + config
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "company": COMPANY,
        "agents": list(AGENTS.keys()),
        "bookings": len(bookings()),
        "escalations": len(escalations()),
        "telegram_live": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "llm_live": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.get("/api/config")
def config() -> dict:
    return {
        "company": COMPANY,
        "fee": DIAGNOSTIC_FEE_USD,
        "demo_phone": DEMO_PHONE,
        "telegram_bot": BOT_HANDLE,
        "fields": [{"key": k, "label": label} for k, label in REQUIRED_FIELDS],
        "agents": [
            {"key": a.key, "name": a.name, "voice": a.voice, "channel": a.channel,
             "opening": a.opening_line}
            for a in AGENTS.values()
        ],
        "scenarios": [{"key": s.key, "title": s.title, "tag": s.tag,
                       "agent": s.agent, "summary": s.summary}
                      for s in SCENARIOS],
        "telegram_live": bool(os.environ.get("TELEGRAM_BOT_TOKEN")),
        "llm_live": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


# ---------------------------------------------------------------------------
# Call lifecycle
# ---------------------------------------------------------------------------

class StartReq(BaseModel):
    agent: str = "amanda"
    caller: str = "web-demo"


@app.post("/api/call/start")
def call_start(r: StartReq) -> dict:
    return start_call(r.caller, r.agent)


class TurnReq(BaseModel):
    agent: str = "amanda"
    caller: str = "web-demo"
    text: str


@app.post("/api/call/turn")
def call_turn(r: TurnReq) -> dict:
    return handle_turn(r.caller, r.text, r.agent)


class OutboundReq(BaseModel):
    name: str = "Daniel Park"
    phone: str = "+1 415 555 0188"
    problem: str = "Whirlpool dryer not heating"


@app.post("/api/outbound")
def outbound(r: OutboundReq) -> dict:
    return trigger_outbound(r.name, r.phone, r.problem)


# ---------------------------------------------------------------------------
# Scenarios — pre-scripted callers, played automatically by the UI
# ---------------------------------------------------------------------------

@app.get("/api/scenarios/{key}")
def scenario(key: str) -> dict:
    s = next((s for s in SCENARIOS if s.key == key), None)
    if not s:
        return JSONResponse({"error": "unknown scenario"}, status_code=404)
    return {
        "key": s.key,
        "title": s.title,
        "tag": s.tag,
        "agent": s.agent,
        "summary": s.summary,
        "seed": s.seed,
        "lines": s.lines,
    }


# ---------------------------------------------------------------------------
# Read-only feeds for the UI
# ---------------------------------------------------------------------------

@app.get("/api/bookings")
def api_bookings() -> dict:
    return {"bookings": [b.__dict__ for b in bookings()]}


@app.get("/api/escalations")
def api_escalations() -> dict:
    return {"escalations": escalations()}


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

@app.post("/telegram/webhook")
async def tg_webhook(request: Request) -> JSONResponse:
    try:
        handle_update(await request.json())
    except Exception:
        pass
    return JSONResponse({"ok": True})


@app.get("/admin/set-webhook")
def admin_set_webhook(request: Request) -> dict:
    base = str(request.base_url).rstrip("/")
    return set_webhook(base)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (INDEX_HTML
            .replace("__BOT__", BOT_HANDLE)
            .replace("__PHONE__", DEMO_PHONE)
            .replace("__COMPANY__", COMPANY)
            .replace("__FEE__", str(DIAGNOSTIC_FEE_USD)))
