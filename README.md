# Safro Solutions — AI Dispatcher (Yelp / Thumbtack → Vapi outbound in < 2 s)

> A fresh Yelp / Thumbtack lead fires a webhook → the dispatcher runs every
> gate (TCPA, service area by city, business hours, phone present, slot
> available, agent rotation) → Vapi places the call to the **first idle**
> agent in the chain (Tony / Sofia / Amanda) → the customer talks to a
> human-sounding AI → booking lands in the Google Sheet + Telegram alert
> fires. **End-to-end in under 2 seconds from lead to ringing.**

**Live demo:** _deployed on Vercel_  ·  **Stack:** Python · FastAPI · Vapi
(web + phone) · ElevenLabs voices · OpenAI gpt-4o-mini · Deepgram nova-2 ·
Anthropic Claude (post-call extraction) · Telegram Bot API

Built to Maya's 5/20 brief — outbound is primary, inbound is the follow-up.

---

## Two surfaces

| Route | What it is |
|---|---|
| `/` | **Ops dashboard** — the demo Maya asked for. Lead feed, sub-2s router visualization, three-agent floor with availability pills, mock Google Sheet of technician slots, live call panel with Vapi web SDK, queue + retry ladder, bookings log. |
| `/console` | The original conversation engine — Amanda inbound chat console. Useful when there's no mic / no Vapi key, or to scrub the booking flow turn-by-turn. |

---

## What's real vs. dry-run

| Piece | Demo | Production |
|---|---|---|
| Lead webhook | One-click sample fire AND real `POST /api/leads/webhook` | same |
| Router timings | Real wall-clock with simulated step latencies that match prod (Sheets ~240 ms, geocode ~65 ms) | identical shape; real APIs swap in |
| Voice | **Vapi** in browser (web call) — multilingual `eleven_turbo_v2_5`, gpt-4o-mini, Deepgram nova-2 | same Vapi config; phone delivery over Twilio |
| **Telegram alert** | **real** (open the bot, /start, then fire a lead) | same |
| Google Sheet of slots | Visual mock | gspread + a real Sheet ID (or KickStarter CRM → Google Calendar) |
| SMS confirmation | Dry-run logged | Twilio (10DLC pending) |
| Retry ladder | 20 min → 24 h → 72 h, max 3, visible in queue panel | same, fires from a worker |
| Out-of-hours queue | Fires at next 7:00 AM, visible in queue panel | same |
| Transcript → booking | Anthropic `claude-sonnet-4-6` parses the call transcript into the 10 required fields | same |

Without `VAPI_PUBLIC_KEY` the routing + queue + sheet flows still fully
work; the call panel prints what would happen and the `/console` chat is
the conversation fallback.

---

## Three agents

| Agent | Channel | Voice (ElevenLabs) | Languages |
|---|---|---|---|
| **Amanda** | inbound | Sarah — warm, calm, professional | English |
| **Tony**   | outbound | Charlie — friendly, confident, not robotic | English |
| **Sofia**  | outbound | Matilda — warm, bilingual ES/EN, auto-switches | English + Spanish |

Routing chains (first idle wins):
- English outbound: Tony → Sofia → Amanda
- Spanish outbound: Sofia → Tony → Amanda
- Inbound: Amanda → Tony → Sofia

---

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn frontdesk.main:app --reload   # http://localhost:8000
```

Env (all optional — the demo runs without any of them):

- `VAPI_PUBLIC_KEY` — required for the in-browser Vapi web call to start.
- `VAPI_API_KEY` — required only for server-side outbound (placing a real
  phone call, milestone 1).
- `ANTHROPIC_API_KEY` — used by the post-call transcript parser and by the
  fallback chat console.
- `TELEGRAM_BOT_TOKEN` (+ optional `TELEGRAM_OWNER_CHAT_ID`) — turns the
  Telegram alert real.
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM` — turn SMS
  real (production).

---

## API surface

| Endpoint | Purpose |
|---|---|
| `GET /` | ops dashboard |
| `GET /console` | chat console (Amanda inbound) |
| `GET /api/config` | agents, fields, sample leads, service-area cities, integration status |
| `POST /api/leads/simulate` `{key}` | fire one of the six pre-built sample leads |
| `POST /api/leads/webhook` | real Yelp / Thumbtack webhook receiver |
| `GET /api/leads`, `GET /api/leads/{id}` | recent leads + their routing decisions |
| `GET /api/agents/status` | current idle/busy per agent |
| `GET /api/queue` | after-hours + retry queue |
| `GET /api/slots` | mock Google Sheet of technician slots |
| `POST /api/vapi/start` `{lead_id}` | build inline Vapi assistant config, lock the agent |
| `POST /api/vapi/event` `{call_id, kind, …}` | browser bridge for Vapi SDK events |
| `POST /api/vapi/webhook` | direct webhook from Vapi (production path) |
| `GET /api/bookings`, `GET /api/escalations` | confirmed records |
| `POST /api/demo/reset` | wipe demo state |
| `POST /telegram/webhook`, `GET /admin/set-webhook` | Telegram passthrough |

---

## Built by

**Waseem Iftikhar** — AI / backend engineer · voice receptionists, lead
automation, messaging integrations.
