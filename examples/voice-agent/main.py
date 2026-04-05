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

# Load env from the example folder first (so `VOICE__ENABLED=true` etc. is picked up
# even when running from the repo root), then fall back to the working directory.
example_env = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=example_env, override=False)
load_dotenv(override=False)

# Debug: print provider (non-sensitive) and mask API key presence
print("VOICE__STT_PROVIDER:", os.environ.get("VOICE__STT_PROVIDER"))
print("VOICE__STT_API_KEY set:", bool(os.environ.get("VOICE__STT_API_KEY")))

from bindu.penguin.bindufy import bindufy


async def handler(messages: list[dict[str, str]]):
    """Streaming voice-friendly handler (async generator).

    This demonstrates true "start speaking while thinking" behavior: the voice
    bridge can forward partial text chunks to TTS as they are yielded.
    """
    latest = messages[-1].get("content", "") if messages else ""
    full = (
        "I heard you say: "
        f"{latest}. "
        "You can keep speaking and I will respond turn by turn."
    )

    words = full.split()
    built: list[str] = []
    for word in words:
        built.append(word)
        # Yield cumulative text (common streaming pattern). The bridge will emit only deltas.
        yield " ".join(built)
        await asyncio.sleep(0.02)


config = {
    "author": "voice-example@getbindu.com",
    "name": "voice_agent_example",
    "description": "A voice-enabled example agent for Bindu.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "voice": {
        "stt_provider": "deepgram",
        "stt_model": "nova-3",
        "stt_language": "en",
        "tts_provider": "elevenlabs",
        "tts_voice_id": "21m00Tcm4TlvDq8ikWAM",
        "tts_model": "eleven_flash_v2_5",
        "sample_rate": 16000,
        "allow_interruptions": True,
        "vad_enabled": True,
    },
}


if __name__ == "__main__":
    bindufy(config=config, handler=handler)
