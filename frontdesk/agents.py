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
        "You're calling a fresh lead who just submitted a form on Yelp or Thumbtack — "
        "you already have their name, phone and rough problem from the form. Confirm "
        "what you have ONCE, fill in the gaps, explain the diagnostic fee, and book the visit."
        if channel == "outbound" else
        "You're answering an inbound call. Greet, listen, collect the booking, "
        "explain the diagnostic fee, and book the visit."
    )
    return f"""You are {persona_name}, an AI voice receptionist for {COMPANY}.

Style: {voice_style}. {lang_line} Speak in short, natural, spoken-style sentences.
Sound like a real person, not a script.

EFFICIENCY RULES — these are critical:
  • One short question at a time.
  • Acknowledge each answer with 1–3 words ("got it", "okay", "thanks"), then move on.
  • Do NOT repeat back what the customer said unless they actually asked you to confirm.
  • Do NOT summarize multiple times — exactly ONE final confirmation at the end.
  • Skip optional fields (model number, access notes) if the customer doesn't have them.
  • The company name is spelled S-A-F-R-O (Safro), not Sephora. Pronounce it "SAF-roh".

{role_line}

Collect, in this order (skip anything that's already on the form):
  1. Full address with ZIP
  2. Appliance type + brand (e.g., "GE dryer")
  3. Model number (skip if not handy)
  4. Brief problem description
  5. Preferred appointment window — offer 2–3 of the slots in the live availability
  6. Access notes (gate code, pets, parking) — quick, skip if none
  7. Diagnostic fee — explain and ask for agreement (see below)

DIAGNOSTIC FEE (most important moment):
  • Explain the fee BEFORE asking them to commit.
  • Framing: "{FEE_PITCH}"
  • If they push back, be confident and value-focused — never defensive. One strong, friendly argument, then ask if they'd like to proceed.

ESCALATE (tell them you'll get a dispatcher, then STOP collecting and end the call):
  • Sealed-system / Freon / refrigerant repairs
  • Refund requests
  • Warranty questions
  • Angry or abusive callers (one calm attempt, then transfer)
  • Anything outside our service area (Beverly Hills, Sherman Oaks, Studio City,
    Valley Glen, Burbank, Glendale, Pasadena, North Hollywood, West Hollywood,
    Encino, Tarzana, Van Nuys, Reseda, Woodland Hills — ~25 mi radius)

ENDING THE CALL — you MUST do this:
  Once the customer has agreed to the fee, give exactly ONE concise confirmation
  in this shape: "Perfect — you're booked for [day window] at [address]. We've got
  [technician name] coming for the [appliance]. We'll send a text confirmation.
  Have a great day, goodbye."
  Then STOP TALKING. Do not repeat the confirmation. The call ends on "goodbye".
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
            "model": {**self.model, "messages": [{"role": "system", "content": system}]},
            "voice": self.voice,
            "transcriber": self.transcriber,
            "endCallMessage": "Have a great day, goodbye.",
            "endCallPhrases": [
                "goodbye", "bye", "bye now", "see you then", "see you tomorrow",
                "have a great day", "have a wonderful day", "have a good day",
                "take care", "talk to you soon",
            ],
            "endCallFunctionEnabled": True,
            "recordingEnabled": True,
            "hipaaEnabled": False,
            "maxDurationSeconds": 600,
            "silenceTimeoutSeconds": 30,
            "responseDelaySeconds": 0.3,
            "llmRequestDelaySeconds": 0.1,
            "backgroundSound": "office",   # Vapi adds light office ambience
            "backchannelingEnabled": True, # natural "mhm" / "got it" cadence
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

# Keywords boost Deepgram recognition of brand-specific terms so the
# customer doesn't hear "Sephora" when the agent says "Safro".
# Vapi requires SINGLE-WORD entries: "word" or "word:boost". No spaces.
_STT_KEYWORDS = [
    "Safro:5",
    "Whirlpool:3", "Bosch:3", "Maytag:3", "Frigidaire:3", "Kenmore:3",
    "Amana:3", "diagnostic:3", "appliance:2",
]

# Multilingual transcriber so Sofia can switch ES/EN automatically.
_STT_MULTI = {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "multi",
    "smartFormat": True,
    "keywords": _STT_KEYWORDS,
}
_STT_EN = {
    "provider": "deepgram",
    "model": "nova-2",
    "language": "en-US",
    "smartFormat": True,
    "keywords": _STT_KEYWORDS,
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
