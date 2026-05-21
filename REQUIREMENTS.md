# Safro Solutions AI Dispatcher — agreed scope (post-call 5/20)

Captured directly from Maya's call. Anything in this doc that's wrong or
incomplete — flag it before milestone 1 starts and I'll revise.

---

## Goal

Replace the human-dispatch loop that takes ≈1 minute to call a fresh Yelp /
Thumbtack lead with an AI dispatcher that calls in **2 seconds or less** and
books on the same call. First mover wins the job in this market.

---

## Outbound (priority — demo first)

### Trigger

- New lead webhook from **Yelp Lead Webhook** or **Thumbtack Pro**, hitting
  `POST /api/leads/webhook`. The lead arrives with: source, customer name,
  phone (sometimes blank), city, problem text, language hint, opt-in flag.

### Routing pipeline (must complete ≤ 2 000 ms)

1. **Parse** the webhook (HMAC-verified in prod).
2. **TCPA / opt-in** — skip the call if no consent; send a text instead.
3. **Service area** — match by **city name** (Beverly Hills, Sherman Oaks,
   Studio City, etc. within ~25 mi). Per your call: no ZIP-code lookups —
   too slow and confuses the AI. City list is editable.
4. **Business hours** — 7 AM – 7 PM PT. **Outside hours → queue for next
   7:00 AM**, do not call. A Telegram alert fires immediately so the
   dispatcher knows about it.
5. **Phone number** — if the form had no phone, send a text via the
   platform DM / SMS instead of trying to call.
6. **Slot availability** — peek the technician schedule (Google Sheet
   today; KickStarter CRM / Google Calendar later). At least one free
   slot or the AI doesn't promise a time.
7. **Agent rotation** — three voice assistants: Tony (outbound primary,
   English), Sofia (bilingual ES/EN), Amanda (inbound primary, outbound
   overflow). Overflow chains:
   - English outbound: Tony → Sofia → Amanda
   - Spanish outbound: Sofia → Tony → Amanda
   The first **idle** agent in the chain picks up; if all busy, queue.

### Call

- **Vapi** web/phone call with the picked agent's config: ElevenLabs voice
  (multilingual `eleven_turbo_v2_5`), OpenAI gpt-4o-mini for the LLM,
  Deepgram nova-2 transcriber (multi-language for Sofia), light office
  background ambience, **0.4 s response delay** so the cadence is natural.
- **Spanish auto-switch** — Sofia greets in ES and switches if the customer
  speaks ES; Tony and Amanda stay English. Future: add fr/pt on request.
- **Google LSA pre-roll** — Vapi's `silenceTimeoutSeconds` is set so the
  agent waits past the "this call from Google" robot announcement before
  starting.

### Conversation

The agent collects, in natural spoken conversation:

- Customer name
- Phone number (confirm if already on the form)
- Full address with ZIP
- Appliance type
- Brand
- Model number if available
- Problem description
- Preferred appointment window
- Access notes (gate code, pets, parking)
- Explicit agreement to the **diagnostic fee** before booking

**Diagnostic-fee handling** is critical — the agent leads with the fee,
frames it as helping the customer save money (not collecting a fee), and
lands the full argument when they hesitate: technician travel, fuel,
expertise, time inspecting, real-cause diagnosis, written estimate,
reserved time slot. Never defensive, never apologetic.

**Escalation paths** (transfer to dispatcher, stop collecting):
- Sealed-system / Freon / refrigerant
- Refund requests
- Warranty questions
- Angry callers (after one calm de-escalation)
- Anything outside the service area

### Confirmation

- Telegram alert on every lead arrival (call placed, queued, sms, or
  rejected) and every booking + escalation.
- SMS confirmation to the customer (Twilio — currently 10DLC pending).
- Booking written to Google Sheet (mocked in demo) and Slot marked taken.

### Retry ladder for unanswered calls

- Attempt 1: place call.
- No answer / busy → wait 20 min → retry.
- Still no answer → wait 24 h → retry.
- Still no answer → wait 72 h → final retry.
- After 3 attempts: stop (Yelp anti-spam policy).

### Multiple leads same time / queueing priority

To finalize:
- If two leads arrive simultaneously and only one agent is free, the
  current rule is **first in, first out**.
- If you'd prefer prioritising (e.g., Yelp over Thumbtack, or Beverly
  Hills over edge-of-area), tell me and I'll wire it.

---

## Inbound (separate demo — follow-up)

### Trigger

- Customer dials the published Safro number → Twilio → Vapi inbound assistant.

### Agent

- Amanda by default; if Amanda's busy → Tony → Sofia.

### Conversation

- Same collection list and same fee handling as outbound.
- Same escalation paths.

### Slot availability

- Real **Google Calendar** read (per your ask): "Mike has 10 AM
  Tuesday booked, Carlos doesn't — Amanda offers Carlos's slot."
- Today the demo uses a Google **Sheet**; Calendar integration is the
  milestone-1 swap.

### After-hours inbound

- Outside business hours, Amanda offers a callback at next business open
  instead of trying to book live.

---

## Hosting + cost

- **Vapi** — ~$50–100/month for ≈100 calls × 3 min avg (Maya's estimate).
  Voice quality varies by model picked.
- **Vercel** — current host. Production OK.
- **Telegram** — free.
- **Twilio SMS** — small per-message cost once 10DLC clears.
- **Anthropic** — for transcript-to-booking parsing (post-call only).
  ≈$0.01 / booking.

---

## What I owe you next

1. The outbound demo, deployed on the same Vercel URL (this build).
2. The voice shortlist from Vapi for you to pick from.
3. The inbound demo with the Google Calendar wire-up.
4. A simple admin to edit the city list, business hours, retry intervals,
   and brand line without touching code.

— Waseem
