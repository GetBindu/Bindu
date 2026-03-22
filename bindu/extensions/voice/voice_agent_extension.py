"""Voice Agent Extension for real-time voice conversations.

This module provides the VoiceAgentExtension class that configures
STT/TTS providers, audio parameters, and session behavior for
voice-enabled Bindu agents.
"""

from __future__ import annotations

from functools import cached_property
from typing import Any, Optional

from bindu.common.protocol.types import AgentExtension
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.voice_agent_extension")


class VoiceAgentExtension:
    """Voice extension for real-time voice agent conversations.

    Configures the voice pipeline (STT, TTS, VAD) and exposes
    a discoverable ``AgentExtension`` in the agent card so clients
    know the agent supports voice.
    """

    def __init__(
        self,
        stt_provider: str = "deepgram",
        stt_model: str = "nova-3",
        stt_language: str = "en",
        tts_provider: str = "elevenlabs",
        tts_voice_id: str = "21m00Tcm4TlvDq8ikWAM",
        tts_model: str = "eleven_turbo_v2_5",
        sample_rate: int = 16000,
        allow_interruptions: bool = True,
        vad_enabled: bool = True,
        description: Optional[str] = None,
    ):
        self.stt_provider = stt_provider
        self.stt_model = stt_model
        self.stt_language = stt_language
        self.tts_provider = tts_provider
        self.tts_voice_id = tts_voice_id
        self.tts_model = tts_model
        self.sample_rate = sample_rate
        self.allow_interruptions = allow_interruptions
        self.vad_enabled = vad_enabled
        self._description = description

        # Validate audio config eagerly
        from .audio_config import validate_sample_rate

        validate_sample_rate(sample_rate)

        logger.info(
            f"VoiceAgentExtension created: STT={stt_provider}/{stt_model}, "
            f"TTS={tts_provider}/{tts_voice_id}, rate={sample_rate}Hz"
        )

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Return AgentExtension metadata for the agent card."""
        return AgentExtension(
            uri=app_settings.voice.extension_uri,
            description=self._description or app_settings.voice.extension_description,
            required=False,  # Clients can still use text
            params={
                "stt_provider": self.stt_provider,
                "tts_provider": self.tts_provider,
                "sample_rate": self.sample_rate,
                "allow_interruptions": self.allow_interruptions,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for logging/debugging."""
        return {
            "stt_provider": self.stt_provider,
            "stt_model": self.stt_model,
            "stt_language": self.stt_language,
            "tts_provider": self.tts_provider,
            "tts_voice_id": self.tts_voice_id,
            "tts_model": self.tts_model,
            "sample_rate": self.sample_rate,
            "allow_interruptions": self.allow_interruptions,
            "vad_enabled": self.vad_enabled,
        }

    def __repr__(self) -> str:
        return (
            f"VoiceAgentExtension(stt={self.stt_provider}/{self.stt_model}, "
            f"tts={self.tts_provider}/{self.tts_voice_id})"
        )
