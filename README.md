# FrontDesk — AI Voice Receptionist & Booking Assistant

> Inbound "call" → AI collects the booking in conversation → appointment booked → confirmation delivered to **Telegram (real)** + SMS → logged. Plus an outbound auto-call path. Built against the Twilio / SMS / Telegram receptionist brief.

**Live demo:** _deployed on Vercel (Python runtime)_ · **Stack:** Python · FastAPI · Telegram Bot API · Anthropic (optional) · Vercel

## Scopes

- **Scope 1 — Inbound:** caller → AI receptionist slot-fills (name, service, phone, time) → offers concrete slots → books → Telegram + SMS confirmation → logged.
- **Scope 2 — Outbound:** a new lead triggers an automated outbound call that books through the same path. Production adds the answer/no-answer retry ladder (max 3 over ~3 days).

## What's real vs. dry-run

| Piece | Demo | Production |
|---|---|---|
| Conversation | deterministic slot-fill (+ optional Anthropic polish) | same + voice platform (Vapi/Retell) |
| **Telegram** | **real** — tap Start on the bot, the confirmation arrives in your chat | same |
| SMS | dry-run logged | Twilio |
| Voice telephony | web simulator | Twilio number → voice agent |
| Store / calendar | in-memory | Postgres + Google Calendar |

Telegram, SMS and the store sit behind interfaces — credentials are configuration, not a rewrite. With no keys at all the demo still completes every booking.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn frontdesk.main:app --reload   # http://localhost:8000
```

Set `TELEGRAM_BOT_TOKEN` to make Telegram live; `ANTHROPIC_API_KEY` to make replies sound natural. `GET /admin/set-webhook` registers the Telegram webhook to the running URL.

## Endpoints

`GET /` simulator · `POST /sim` conversation turn · `POST /outbound` outbound auto-call · `POST /telegram/webhook` Telegram updates · `GET /api/bookings` log · `GET /health`

## Built by

**Waseem Iftikhar** — AI / Backend Engineer · voice receptionists, booking automation, messaging integrations.
