# Safro Solutions Appliance Repair — AI Receptionist & Booking

> Inbound caller dials in → **Amanda** (warm intake) takes the booking in
> conversation, explains the diagnostic fee with confidence, escalates the
> sensitive stuff (sealed-system, refunds, warranty, angry, out-of-area), and
> fires the confirmation to **Telegram (real)** + SMS + log. Plus **Tony**,
> the outbound agent who calls a fresh Yelp / Thumbtack lead and books on the
> same path.

**Live demo:** _deployed on Vercel (Python runtime)_ · **Stack:** Python · FastAPI · Anthropic Claude · Telegram Bot API · Vercel

Built to the brief Maya laid out on the 5/20 call: two agents (Amanda + Tony),
the Safro Solutions opening line, all ten intake fields, the fee-objection
value pitch, and every escalation path.

---

## What's in the demo

- **Two agents**, switchable in the header:
  - **Amanda — inbound, warm/calm/professional.** Opens with _"Thank you for calling Safro Solutions Appliance Repair. This is Amanda. How can I help you today?"_
  - **Tony — outbound, friendly/confident/not-robotic.** Seeded with the lead's name + phone + problem (the form they just submitted) and books from there.
- **Live intake panel** — every required field lights up the moment Amanda extracts it: name, phone, full address + ZIP, appliance, brand, model, problem, window, access notes, and the diagnostic-fee agreement.
- **Diagnostic-fee value pitch** — the agents lead with the fee _before_ booking and use the full "travel · expertise · diagnosis · estimate · reserved slot" argument when the caller hesitates. Bookings only confirm after explicit agreement.
- **Escalation** — sealed-system / Freon, refund requests, warranty questions, angry callers (after one calm de-escalation), and anything outside the service area route to a human dispatcher and emit a Telegram alert.
- **Confirmations** — every booking hits Telegram (real if bot configured), SMS (dry-run in demo, Twilio in prod), and the in-app log.
- **Scenario player** — six pre-scripted callers (happy booking, fee objection, sealed-system, out-of-area, angry, Tony outbound) play through the same real engine so it's not a recording.

## What's real vs. dry-run

| Piece | Demo | Production |
|---|---|---|
| Conversation | Claude Sonnet 4.6 (JSON-mode, per-turn field extraction + escalation) | same, behind the voice agent |
| **Telegram** | **real** — Start the bot, finish a booking, the confirmation arrives in your chat | same |
| SMS | dry-run logged | Twilio |
| Voice telephony | web simulator | Twilio number → Vapi / Retell |
| Store / calendar | in-memory | Postgres + Google Calendar |
| Outbound retry ladder | one-shot demo | answer/no-answer ladder over ~3 days |

With **no keys at all** the demo still completes every flow — there's a deterministic walker behind the same interface so the conversation never dead-ends.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn frontdesk.main:app --reload   # http://localhost:8000
```

Optional env:
- `ANTHROPIC_API_KEY` — makes Amanda + Tony talk naturally instead of using the scripted fallback. `ANTHROPIC_MODEL` defaults to `claude-sonnet-4-6`.
- `TELEGRAM_BOT_TOKEN` — makes the Telegram confirmation real. `GET /admin/set-webhook` registers the webhook to the running URL.
- `TELEGRAM_OWNER_CHAT_ID` — pin the confirmation to one chat instead of broadcasting to every chat that has /start-ed.
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_FROM` — turn SMS real.

## API

| Endpoint | Purpose |
|---|---|
| `GET /` | the demo console |
| `GET /api/config` | agents, fields, scenarios, integration status |
| `POST /api/call/start` `{agent}` | start a fresh inbound call (Amanda) |
| `POST /api/call/turn` `{agent, text}` | one conversational turn |
| `POST /api/outbound` `{name, phone, problem}` | Tony places a callback |
| `GET /api/scenarios/{key}` | fetch a scripted scenario (UI plays it) |
| `GET /api/bookings` | confirmed bookings (in-memory) |
| `GET /api/escalations` | escalation log |
| `POST /telegram/webhook` | Telegram update sink |
| `GET /admin/set-webhook` | register the Telegram webhook |
| `GET /health` | health + integration status |

## How the agents are wired

`frontdesk/agents.py` holds the personas, the required-field schema, the
escalation reasons, and the diagnostic-fee value pitch.
`frontdesk/brain.py` ships the running transcript to Claude with a strict
JSON contract — `{reply, fields, escalate, ready_to_book}` — and parses
the result; if the LLM is unavailable the same module walks the caller
through a deterministic version of the same flow.
`frontdesk/pipeline.py` turns `ready_to_book` into a real booking +
Telegram broadcast + SMS, or `escalate` into a dispatcher alert.

## Built by

**Waseem Iftikhar** — AI / Backend Engineer · voice receptionists, booking automation, messaging integrations.
