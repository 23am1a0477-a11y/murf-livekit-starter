import importlib.util
import json
import logging
import os

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Support both `uv run python src/agent.py dev` (script) and installed-package imports
try:
    from .database import init_db, lookup_caller, save_caller
except ImportError:
    from database import init_db, lookup_caller, save_caller  # type: ignore[no-redef]

load_dotenv(".env.local")

logger = logging.getLogger("agent")

# Initialise the caller-memory database once at import time
init_db()

# Change this prompt to change what your voice agent does.
# See README.md for example prompts (customer support, language tutor, receptionist).
prompt_path = os.path.join(
    os.path.dirname(__file__), "agent_starter_python.egg-info", "prompt.py"
)
if os.path.exists(prompt_path):
    spec = importlib.util.spec_from_file_location("prompt", prompt_path)
    prompt_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(prompt_module)
    SYSTEM_PROMPT = getattr(prompt_module, "SYSTEM_PROMPT", "")
else:
    SYSTEM_PROMPT = """You are a friendly and efficient customer support agent for a tech company. Help users with account issues, billing questions, and product troubleshooting. Be concise, empathetic, and solution-oriented. If you don't know something, say so honestly and offer to escalate. Your responses are concise and without complex formatting, emojis, or symbols."""

# ── Caller-memory instructions appended to every prompt ──────────────────────
MEMORY_PROMPT = """

## CALLER MEMORY

You have access to two tools: `lookup_caller_profile` and `save_caller_profile`.

### At the start of every call
1. Call `lookup_caller_profile` with the caller's user_id (provided in the session context below).
2. If a record is found, greet the caller warmly by name and briefly reference the last topic discussed.
   Example: "Welcome back, Priya! Last time we spoke about the Kisan Credit Card scheme — did that help? How can I assist you today?"
3. If no record is found, greet them as a new caller and proceed normally.

### Saving information (CONSENT REQUIRED — Financial Services hard rule)
- Before saving anything, explicitly ask the caller:
  "Before we finish, may I remember a few details — just your name and the schemes we discussed today — so I can serve you better next time? I will never store your account or ID details."
- If they agree: call `save_caller_profile` with what you learned (name, language preference, schemes/topics discussed, eligibility answers given). Do NOT include account numbers, PAN, Aadhaar, OTP, PIN, or any security credentials.
- If they decline or are unsure: do NOT call `save_caller_profile`. Acknowledge politely: "No problem at all — your details will not be saved."
- Never save anything without explicit verbal consent.

### What you may save in `facts`
- Scheme names the caller asked about (e.g. "Kisan Credit Card", "PM Awas Yojana")
- Eligibility answers already given (e.g. income bracket, farm size category)
- Preferred contact channel (app / branch / call)
- Any other non-sensitive context that helps future calls

### What you must NEVER save
- Account numbers, loan account IDs, card numbers
- PAN, Aadhaar, Voter ID, or any government ID number
- OTP, PIN, passwords, or security credentials
- Credit scores, account balances, or transaction data
"""


class Assistant(Agent):
    def __init__(self, caller_profile: dict | None, user_id: str) -> None:
        # Build a context header so the LLM knows who it is speaking to
        if caller_profile:
            context = (
                f"\n\n[SESSION CONTEXT]\n"
                f"user_id: {user_id}\n"
                f"Returning caller: YES\n"
                f"Name: {caller_profile.get('name', 'unknown')}\n"
                f"Language preference: {caller_profile.get('language_preference', 'en')}\n"
                f"Last interaction: {caller_profile.get('last_interaction', 'unknown')}\n"
                f"Known facts: {json.dumps(caller_profile.get('facts', {}), ensure_ascii=False)}\n"
                f"[END SESSION CONTEXT]"
            )
        else:
            context = (
                f"\n\n[SESSION CONTEXT]\n"
                f"user_id: {user_id}\n"
                f"Returning caller: NO\n"
                f"[END SESSION CONTEXT]"
            )

        super().__init__(instructions=SYSTEM_PROMPT + MEMORY_PROMPT + context)
        self._user_id = user_id

    # ── Tool 1: Look up a caller ───────────────────────────────────────────────
    @function_tool
    async def lookup_caller_profile(self, context: RunContext, user_id: str):
        """Look up a caller's saved profile by their user_id.

        Call this at the very start of the conversation to find out if this is a
        returning caller. Returns their name, language preference, known facts, and
        last interaction timestamp — or a message indicating no record exists.

        Args:
            user_id: The caller's stable unique identifier (provided in the session context).
        """
        logger.info("Tool called: lookup_caller_profile user_id=%s", user_id)
        record = lookup_caller(user_id)
        if record is None:
            return f"No record found for user_id '{user_id}'. This is a new caller."
        return (
            f"Caller found.\n"
            f"Name: {record.get('name', '')}\n"
            f"Language preference: {record.get('language_preference', 'en')}\n"
            f"Last interaction: {record.get('last_interaction', '')}\n"
            f"Known facts: {json.dumps(record.get('facts', {}), ensure_ascii=False)}"
        )

    # ── Tool 2: Save a caller's profile ───────────────────────────────────────
    @function_tool
    async def save_caller_profile(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        language_preference: str,
        schemes_discussed: str,
        eligibility_answers: str,
    ):
        """Save (or update) a caller's profile after obtaining their verbal consent.

        IMPORTANT: Only call this tool AFTER the caller has explicitly agreed to have
        their details saved. Never call this without consent.
        Never include account numbers, PAN, Aadhaar, OTP, PIN, or any sensitive data.

        Args:
            user_id: The caller's stable unique identifier.
            name: The caller's preferred name as they stated it.
            language_preference: Language or mix used (e.g. "en", "hi-en", "ta-en").
            schemes_discussed: Comma-separated list of financial schemes mentioned (e.g. "Kisan Credit Card, PM Awas Yojana").
            eligibility_answers: Brief summary of eligibility answers given (e.g. "annual income < 3L, owns < 2 acres farmland"). Must NOT contain any ID or account numbers.
        """
        logger.info(
            "Tool called: save_caller_profile user_id=%s name=%s", user_id, name
        )

        facts = {}
        if schemes_discussed.strip():
            facts["schemes_discussed"] = [
                s.strip() for s in schemes_discussed.split(",") if s.strip()
            ]
        if eligibility_answers.strip():
            facts["eligibility_answers"] = eligibility_answers.strip()

        record = {
            "user_id": user_id,
            "name": name,
            "language_preference": language_preference,
            "facts": facts,
        }
        save_caller(record)
        return (
            f"Profile saved successfully for {name}. "
            f"Schemes noted: {schemes_discussed}. "
            f"I will greet them by name next time."
        )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Join the room first so we can read remote participant identities
    await ctx.connect()

    # Derive a stable user_id from the first human participant's identity.
    # The frontend sends a stable UUID (stored in localStorage) as participantIdentity.
    user_id = "unknown"
    for participant in ctx.room.remote_participants.values():
        identity = participant.identity or ""
        # Skip agent workers (they conventionally include "agent" in their identity)
        if "agent" not in identity.lower():
            user_id = identity
            break
    # Fallback: use room name so at least the session is identifiable in logs
    if user_id == "unknown":
        user_id = ctx.room.name

    logger.info("Session user_id resolved to: %s", user_id)

    # Look up the caller — pass profile into Assistant for personalised greeting
    caller_profile = lookup_caller(user_id)
    if caller_profile:
        logger.info(
            "Returning caller detected: name=%s last=%s",
            caller_profile.get("name"),
            caller_profile.get("last_interaction"),
        )
    else:
        logger.info("New caller — no existing profile found.")

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    # Start the session, which initialises the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(caller_profile=caller_profile, user_id=user_id),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
