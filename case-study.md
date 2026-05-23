# FrontDesk-AI — Multi-Agent AI Dispatcher (lead → outbound call in under 2 s)

**Live demo:** https://frontdesk-ai-zeta.vercel.app

## The problem

Service businesses (home services, salons, clinics) running on Yelp /
Thumbtack lose leads in seconds. The first vendor to call back wins.
A staffed reception desk that can answer every inbound lead in under two
seconds — across multiple voice agents, only ringing when the area, hours,
slot and TCPA checks pass — is the right shape, but it needs to be both
real-time and reliable.

## The build

A FastAPI service with two surfaces: an **ops dashboard** showing the live
lead feed, a sub-2-second router visualisation, a three-agent floor with
availability pills, the mock Sheet of technician slots, and a Vapi-powered
web-call panel; and an **inbound chat console** for offline scrub of the
booking conversation. The dispatcher runs every gate (TCPA, service-area by
city, business hours, phone present, slot available, agent rotation) and
hands the call to the **first idle** AI agent in the chain (Tony / Sofia /
Amanda). Vapi places the call, the customer talks to a human-sounding
multilingual voice, and the booking lands in the Google Sheet with a real
Telegram alert to the owner.

## Architecture

```
Yelp / Thumbtack webhook
   → POST /api/leads/webhook → dispatcher gates (TCPA · area · hours · slot · rotation)
   → first idle agent in chain (Tony · Sofia · Amanda)
   → Vapi places call (ElevenLabs voice · OpenAI gpt-4o-mini · Deepgram nova-2)
   → live AI conversation
   → Anthropic Claude extracts the 10 booking fields from the transcript
   → Google Sheet write + Telegram alert + retry ladder (20 min · 24 h · 72 h)
   → out-of-hours queue fires at 7:00 AM next day
```

## Why it matters

- **Sub-2-second time-to-call** — every gate runs in parallel with real
  wall-clock latencies that match production (Sheets ~240 ms, geocode ~65 ms).
- **Multi-agent rotation** — three AI receptionists with availability tracking
  so one slow caller does not stall the queue.
- **Real where it counts** — Telegram alerts fire for real; the call is a real
  Vapi web call; transcript-to-booking parsing is a real Anthropic call. The
  Sheet and SMS are visual mocks (one-config-line swap to live).
- **Graceful out-of-hours** — the queue fires at next business hours; retry
  ladder (20 min → 24 h → 72 h, max three) prevents missed leads.

## Stack

Python · FastAPI · Vapi (web + phone) · ElevenLabs voices · OpenAI gpt-4o-mini · Deepgram nova-2 · Anthropic Claude · Telegram Bot API · Vercel

---

**Waseem Iftikhar** — AI / Backend Engineer
