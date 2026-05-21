"""Three AI agents for Safro Solutions Appliance Repair.

Each agent has a persona, a voice config that Vapi consumes (11labs
turbo_v2_5 multilingual under the hood — same TTS Vapi uses, so the
demo voice is production voice), an LLM/transcriber config, and the
system prompt + first line Vapi will speak.

Agents:
  - Amanda — inbound intake.  Warm, calm, professional, natural.
  - Tony   — outbound primary.  Calls Yelp/Thumbtack leads in <2s.
             Friendly, confident, helpful, not robotic.
  - Sofia  — outbound bilingual (English ↔ Spanish), per Maya's brief.
             Switches language automatically when caller speaks Spanish.

Specialty routing rule:
  * Inbound  → Amanda → Tony → Sofia        (overflow chain)
  * Outbound → Tony   → Sofia → Amanda      (overflow chain)
  * Outbound (Spanish-language hint) → Sofia → Tony → Amanda
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

COMPANY = "Safro Solutions Appliance Repair"
DIAGNOSTIC_FEE_USD = 89

REQUIRED_FIELDS = [
    ("name",       "Customer name"),
    ("phone",      "Phone number"),
    ("address",    "Full address + ZIP"),
    ("appliance",  "Appliance type"),
    ("brand",      "Brand"),
    ("model",      "Model number (optional)"),
    ("problem",    "Problem description"),
    ("window",     "Preferred appointment window"),
    ("access",     "Access notes (gate code, pets, parking)"),
    ("fee_agreed", "Diagnostic fee accepted"),
]

ESCALATION_REASONS = {
    "sealed_system": "Sealed-system / Freon / refrigerant work",
    "refund":        "Refund request",
    "warranty":      "Warranty question",
    "angry":         "Angry / abusive caller",
    "out_of_area":   "Outside service area",
}

FEE_PITCH = (
    f"Our diagnostic visit is ${DIAGNOSTIC_FEE_USD}. It's not just for showing up — "
    "it covers the technician's travel to your home, fuel and vehicle costs, time "
    "inspecting and diagnosing the appliance, the expertise to find the real cause "
    "instead of guessing, a written estimate and repair recommendation, and "
    "reserving a slot we could have given another customer. We're trying to save "
    "you money by repairing the appliance when it's worth it — not just collect a fee."
)


def _base_system_prompt(persona_name: str, voice_style: str,
                         channel: str, languages: list[str]) -> str:
    lang_line = "Speak " + " or ".join(languages) + (
        ". If the caller starts in Spanish or switches mid-call, switch with them."
        if "Spanish" in languages else "."
    )
    role_line = (
        "You're calling a fresh lead who just submitted a form on Yelp or Thumbtack "
        "— you may already have their name, phone, and rough problem from the form. "
        "Confirm what you have, fill in the gaps, explain the diagnostic fee, and book the visit."
        if channel == "outbound" else
        "You're answering an inbound call to the company line. Greet, listen, "
        "collect the booking, explain the diagnostic fee, and book the visit."
    )
    return f"""You are {persona_name}, an AI voice receptionist for {COMPANY}.

Style: {voice_style}. {lang_line} Speak in short, natural, spoken-style sentences.
One question at a time. Acknowledge what the caller just said before asking the next thing.
Never sound like a script — sound like a real person.

{role_line}

Fields you must collect (in natural conversation, not as a checklist):
  - Customer name
  - Phone number
  - Full address with ZIP code
  - Appliance type (refrigerator, washer, dryer, dishwasher, oven, range, AC, etc.)
  - Brand (Whirlpool, GE, Samsung, LG, Bosch, etc.)
  - Model number if available
  - Problem description
  - Preferred appointment window
  - Access notes (gate code, pets, parking)
  - Explicit agreement to the diagnostic fee

CRITICAL — the diagnostic fee:
  • Always explain the fee BEFORE asking the caller to commit to booking.
  • Use this framing: "{FEE_PITCH}"
  • If they hesitate or push back, be CONFIDENT and value-focused, never defensive.
    Make a strong friendly case, then ask if they'd like to proceed.

Escalate (tell the caller you'll get a dispatcher on it, then stop collecting):
  • Sealed-system / Freon / refrigerant repairs
  • Refund requests
  • Warranty questions
  • Angry or abusive callers (after one calm de-escalation attempt)
  • Anything outside our service area (Beverly Hills, Sherman Oaks, Studio City,
    Valley Glen, Burbank, Glendale, Pasadena, North Hollywood, West Hollywood,
    Encino, Tarzana, Van Nuys, Reseda, Woodland Hills — and ~25-mile radius)

When you've collected every required field and the caller has agreed to the fee,
clearly confirm the booking: name, address, appliance, time window, fee accepted,
and end the call warmly.
"""


@dataclass(frozen=True)
class Agent:
    key: str
    name: str
    voice_style: str
    channel: str
    languages: list[str]
    opening_line: str
    voice: dict[str, Any]          # Vapi voice config (11labs)
    model: dict[str, Any]          # Vapi LLM config
    transcriber: dict[str, Any]    # Vapi STT config

    @property
    def system_prompt(self) -> str:
        return _base_system_prompt(self.name, self.voice_style,
                                    self.channel, self.languages)

    def vapi_assistant(self, lead_context: str = "") -> dict[str, Any]:
        """Inline (transient) Vapi assistant config for /call.

        Vapi accepts the assistant config inline per call — no need to
        pre-create assistants. The full system prompt + first line +
        voice/LLM/STT all travel together. lead_context is appended to
        the system prompt so the assistant knows what the lead form
        already contained.
        """
        system = self.system_prompt
        if lead_context:
            system += "\n\nLead context (from the form they submitted):\n" + lead_context
        return {
            "name": self.name,
            "firstMessage": self.opening_line,
            "model": {**self.model, "systemPrompt": system},
            "voice": self.voice,
            "transcriber": self.transcriber,
            "endCallMessage": "Thanks — we'll see you at your appointment. Have a great day.",
            "endCallPhrases": ["goodbye", "bye now", "see you then"],
            "recordingEnabled": True,
            "hipaaEnabled": False,
            "maxDurationSeconds": 600,
            "silenceTimeoutSeconds": 25,
            "responseDelaySeconds": 0.4,
            "llmRequestDelaySeconds": 0.1,
            "backgroundSound": "office",   # Vapi adds light office ambience
        }


# ── Voice IDs — public ElevenLabs voices Vapi resolves directly ─────────────
# Picked for tone match to Maya's spec (warm/calm / friendly-confident /
# bilingual-natural). All work with the multilingual turbo_v2_5 model.

_VOICE_AMANDA = {
    "provider": "11labs",
    "voiceId": "EXAVITQu4vr4xnSDxMaL",   # Sarah — warm, calm, professional
    "model": "eleven_turbo_v2_5",
    "stability": 0.5,
    "similarityBoost": 0.75,
    "style": 0.3,
    "useSpeakerBoost": True,
}

_VOICE_TONY = {
    "provider": "11labs",
    "voiceId": "IKne3meq5aSn9XLyUdCD",   # Charlie — natural, confident male
    "model": "eleven_turbo_v2_5",
    "stability": 0.45,
    "similarityBoost": 0.75,
    "style": 0.4,
    "useSpeakerBoost": True,
}

_VOICE_SOFIA = {
    "provider": "11labs",
    "voiceId": "XrExE9yKIg1WjnnlVkGX",   # Matilda — warm, multilingual ES/EN
    "model": "eleven_turbo_v2_5",
    "stability": 0.5,
    "similarityBoost": 0.75,
    "style": 0.35,
    "useSpeakerBoost": True,
}

# Fast, low-latency LLM — needed to hit the <2s lead-to-talk budget.
_MODEL_BASE = {
    "provider": "openai",
    "model": "gpt-4o-mini",
    "temperature": 0.55,
    "maxTokens": 250,
    "emotionRecognitionEnabled": True,
}

# Multilingual transcriber so Sofia can switch ES/EN automatically.
_STT_MULTI = {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "multi",
    "smartFormat": True,
}
_STT_EN = {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "smartFormat": True,
}


AMANDA = Agent(
    key="amanda",
    name="Amanda",
    voice_style="warm, calm, professional, natural — speak with patience",
    channel="inbound",
    languages=["English"],
    opening_line=(
        f"Thank you for calling {COMPANY}. This is Amanda. How can I help you today?"
    ),
    voice=_VOICE_AMANDA,
    model=_MODEL_BASE,
    transcriber=_STT_EN,
)

TONY = Agent(
    key="tony",
    name="Tony",
    voice_style="friendly, confident, helpful, not robotic — move with energy",
    channel="outbound",
    languages=["English"],
    opening_line=(
        f"Hi, this is Tony from {COMPANY} — I'm calling about the appliance repair "
        "request you just sent in. Is now a good time to lock in your visit?"
    ),
    voice=_VOICE_TONY,
    model=_MODEL_BASE,
    transcriber=_STT_EN,
)

SOFIA = Agent(
    key="sofia",
    name="Sofia",
    voice_style="warm, bilingual, naturally switches between English and Spanish",
    channel="outbound",
    languages=["English", "Spanish"],
    opening_line=(
        f"Hola, soy Sofia de {COMPANY} — le llamo por la solicitud de reparación "
        "que acaba de enviar. ¿Es buen momento para confirmar su visita? "
        f"(Hi, this is Sofia from {COMPANY} — calling about the repair request "
        "you just sent in. Good time to confirm your visit?)"
    ),
    voice=_VOICE_SOFIA,
    model=_MODEL_BASE,
    transcriber=_STT_MULTI,
)


AGENTS = {a.key: a for a in (AMANDA, TONY, SOFIA)}


def get(key: str) -> Agent:
    return AGENTS.get(key, TONY)


# ─── Routing helper ─────────────────────────────────────────────────────────
# Per Maya's brief: Tony is the outbound primary. Sofia handles Spanish.
# Amanda handles inbound. If the specialty agent is busy, fall through the
# overflow chain.

OUTBOUND_CHAIN = ["tony", "sofia", "amanda"]
INBOUND_CHAIN = ["amanda", "tony", "sofia"]
SPANISH_CHAIN = ["sofia", "tony", "amanda"]


def chain_for(channel: str, prefers_spanish: bool = False) -> list[str]:
    if prefers_spanish:
        return SPANISH_CHAIN
    return INBOUND_CHAIN if channel == "inbound" else OUTBOUND_CHAIN
