"""Factory for creating pipecat STT and TTS service instances.

Creates configured Deepgram STT and ElevenLabs TTS services
from the VoiceAgentExtension configuration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from .voice_agent_extension import VoiceAgentExtension

logger = get_logger("bindu.voice.service_factory")


def create_stt_service(config: VoiceAgentExtension) -> Any:
    """Create a Speech-to-Text service instance.

    Args:
        config: Voice extension configuration.

    Returns:
        Configured pipecat STT service.

    Raises:
        ImportError: If pipecat STT dependencies are not installed.
        ValueError: If the STT API key is not configured.
    """
    api_key = app_settings.voice.stt_api_key
    if not api_key:
        raise ValueError(
            "VOICE__STT_API_KEY is required. Set it in your .env or environment."
        )

    if config.stt_provider == "deepgram":
        try:
            from pipecat.services.deepgram.stt import DeepgramSTTService
        except ImportError as e:
            raise ImportError(
                "Deepgram STT requires pipecat[deepgram]. "
                "Install with: pip install 'bindu[voice]'"
            ) from e

        stt = DeepgramSTTService(
            api_key=api_key,
            model=config.stt_model,
            language=config.stt_language,
        )
        logger.info(
            f"Created Deepgram STT: model={config.stt_model}, lang={config.stt_language}"
        )
        return stt

    raise ValueError(f"Unsupported STT provider: {config.stt_provider}")


def create_tts_service(config: VoiceAgentExtension) -> Any:
    """Create a Text-to-Speech service instance.

    Args:
        config: Voice extension configuration.

    Returns:
        Configured pipecat TTS service.

    Raises:
        ImportError: If pipecat TTS dependencies are not installed.
        ValueError: If the TTS API key is not configured.
    """
    api_key = app_settings.voice.tts_api_key
    if not api_key:
        raise ValueError(
            "VOICE__TTS_API_KEY is required. Set it in your .env or environment."
        )

    if config.tts_provider == "elevenlabs":
        try:
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
        except ImportError as e:
            raise ImportError(
                "ElevenLabs TTS requires pipecat[elevenlabs]. "
                "Install with: pip install 'bindu[voice]'"
            ) from e

        tts = ElevenLabsTTSService(
            api_key=api_key,
            voice_id=config.tts_voice_id,
            model=config.tts_model,
        )
        logger.info(
            f"Created ElevenLabs TTS: voice={config.tts_voice_id}, model={config.tts_model}"
        )
        return tts

    raise ValueError(f"Unsupported TTS provider: {config.tts_provider}")
