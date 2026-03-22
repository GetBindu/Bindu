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

from bindu.penguin.bindufy import bindufy


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Simple voice-friendly echo handler.

    The voice bridge converts speech to text and submits user turns as regular
    text messages to this handler.
    """
    latest = messages[-1].get("content", "") if messages else ""
    return [
        {
            "role": "assistant",
            "content": (
                "I heard you say: "
                f"{latest}. "
                "You can keep speaking and I will respond turn by turn."
            ),
        }
    ]


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
        "tts_model": "eleven_turbo_v2_5",
        "sample_rate": 16000,
        "allow_interruptions": True,
        "vad_enabled": True,
    },
}


if __name__ == "__main__":
    bindufy(config=config, handler=handler)
