"""Voice-configured Bindu agent example.

This example enables the custom voice extension and exposes:
- POST /voice/session/start
- GET  /voice/session/{session_id}/status
- DELETE /voice/session/{session_id}
- WS   /ws/voice/{session_id}

Run:
    uv run examples/voice-agent/main.py
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

# Load env from the example folder first (so `VOICE__ENABLED=true` etc. is picked up
# even when running from the repo root), then fall back to the working directory.
example_env = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=example_env, override=False)
load_dotenv(override=False)

# Debug: print provider (non-sensitive) and mask API key presence
print("VOICE__STT_PROVIDER:", os.environ.get("VOICE__STT_PROVIDER"))
print("VOICE__STT_API_KEY set:", bool(os.environ.get("VOICE__STT_API_KEY")))

from bindu.penguin.bindufy import bindufy


OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip()
OPENROUTER_MEMORY_TURNS = max(
    0,
    int(os.environ.get("OPENROUTER_MEMORY_TURNS", "4") or "4"),
)
VOICE_MAX_SENTENCES = max(
    1,
    int(os.environ.get("VOICE_MAX_SENTENCES", "2") or "2"),
)
_openrouter_client: AsyncOpenAI | None = None


def _get_openrouter_client() -> AsyncOpenAI | None:
    global _openrouter_client

    if not OPENROUTER_API_KEY:
        return None

    if _openrouter_client is None:
        _openrouter_client = AsyncOpenAI(
            api_key=OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
        )

    return _openrouter_client


def _build_openrouter_messages(messages: list[dict[str, str]], latest_text: str) -> list[dict[str, str]]:
    """Build a compact chat history for OpenRouter.

    Keeps only recent user/assistant turns to reduce token usage and latency.
    """
    history: list[dict[str, str]] = []

    for raw in messages:
        role_raw = str(raw.get("role", "user")).strip().lower()
        role_map: dict[str, str] = {
            "agent": "assistant",
            "assistant": "assistant",
            "user": "user",
            "system": "system",
        }
        role = role_map.get(role_raw)
        if not role:
            continue

        content = str(raw.get("content", "")).strip()
        if not content:
            continue

        history.append({"role": role, "content": content})

    # Ensure latest user text is present even if caller didn't attach it as a message yet.
    if latest_text and (not history or history[-1] != {"role": "user", "content": latest_text}):
        history.append({"role": "user", "content": latest_text})

    if OPENROUTER_MEMORY_TURNS > 0:
        max_messages = OPENROUTER_MEMORY_TURNS * 2
        history = history[-max_messages:]
    else:
        # Memory explicitly disabled: only keep latest user request.
        history = [{"role": "user", "content": latest_text}]

    return [
        {
            "role": "system",
            "content": (
                "You are a concise, helpful voice assistant. "
                "Answer in at most 2 short sentences unless the user asks for detail. "
                "Be precise, avoid repetition, and avoid markdown/bullets. "
                "Do not repeat prior phrasing in the same response."
            ),
        },
        *history,
    ]


def _append_stream_piece(current: str, piece: str) -> str:
    """Safely append streamed content that may be delta or cumulative text."""
    incoming = piece or ""
    if not incoming:
        return current
    if not current:
        return incoming

    # Some providers stream cumulative text snapshots.
    if incoming.startswith(current):
        return incoming

    # Ignore exact duplicate tail pieces.
    if current.endswith(incoming):
        return current

    # Merge overlapping suffix/prefix to avoid duplicated phrases.
    max_overlap = min(len(current), len(incoming))
    for overlap in range(max_overlap, 0, -1):
        if current[-overlap:] == incoming[:overlap]:
            return current + incoming[overlap:]

    return current + incoming


def _clamp_sentences(text: str, max_sentences: int) -> tuple[str, bool]:
    """Clamp output to max sentences and report whether truncation happened."""
    if not text.strip():
        return "", False

    sentence_endings = ".!?"
    count = 0
    idx = -1
    for i, ch in enumerate(text):
        if ch in sentence_endings:
            count += 1
            if count >= max_sentences:
                idx = i
                break

    if idx == -1:
        return text.strip(), False

    return text[: idx + 1].strip(), True


async def handler(messages: list[dict[str, str]]):
    """Streaming voice-friendly handler (async generator).

    Uses OpenRouter for real LLM responses when configured, with demo fallback.
    """
    latest = messages[-1].get("content", "") if messages else ""
    text = latest.strip()
    if not text:
        yield "I didn't catch that. Please ask a question, and I'll answer briefly."
        return

    client = _get_openrouter_client()
    if client is not None:
        try:
            llm_messages = _build_openrouter_messages(messages, text)
            stream = await client.chat.completions.create(
                model=OPENROUTER_MODEL,
                temperature=0.4,
                max_tokens=140,
                stream=True,
                messages=llm_messages,  # type: ignore[arg-type]
            )

            built = ""
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if not delta:
                    continue
                built = _append_stream_piece(built, delta)
                clamped, done = _clamp_sentences(built, VOICE_MAX_SENTENCES)
                if clamped:
                    yield clamped
                if done:
                    break

            if not built.strip():
                yield "I couldn't generate a response this time. Please try again."
            return
        except Exception as exc:
            print(f"OpenRouter error: {exc}")

    # Fallback: useful template response when OpenRouter is not configured/available.
    full = (
        f"Here's a concise answer to: {text}. "
        "I'm currently running in demo fallback mode because OpenRouter is not configured or unavailable. "
        "Set OPENROUTER_API_KEY to enable full LLM responses."
    )

    chunks = [chunk.strip() for chunk in full.split(". ") if chunk.strip()]
    built = ""
    for i, chunk in enumerate(chunks):
        segment = chunk if chunk.endswith((".", "?", "!")) else f"{chunk}."
        built = segment if i == 0 else f"{built} {segment}"
        yield built
        await asyncio.sleep(0.08)


config = {
    "author": "voice-example@getbindu.com",
    "name": "voice_agent_example",
    "description": "A voice-enabled example agent for Bindu.",
    "skills": ["skills/voice-brief-response-skill"],
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": [
            origin.strip()
            for origin in os.environ.get(
                "BINDU_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,http://localhost:4173,http://127.0.0.1:4173,http://localhost:3000,http://127.0.0.1:3000",
            ).split(",")
            if origin.strip()
        ],
    },
    "voice": {
        "stt_provider": "deepgram",
        "stt_model": "nova-3",
        "stt_language": "en",
        "tts_provider": "piper",
        "tts_voice_id": "en_US-ryan-high",
        "tts_model": "piper-local",
        "sample_rate": 16000,
        "allow_interruptions": True,
        "vad_enabled": False,
    },
}


if __name__ == "__main__":
    bindufy(config=config, handler=handler)
