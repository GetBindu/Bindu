"""Factory for creating pipecat STT and TTS service instances.

Creates configured Deepgram STT and Piper/ElevenLabs/Azure TTS services
from the VoiceAgentExtension configuration.
"""

from __future__ import annotations

import importlib
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
        logger.warning(
            "STT service configuration incomplete: missing API key",
            setting="VOICE__STT_API_KEY",
        )
        raise ValueError("STT service configuration incomplete")

    if config.stt_provider == "deepgram":
        try:
            deepgram_module = importlib.import_module("pipecat.services.deepgram.stt")
            DeepgramSTTService = getattr(deepgram_module, "DeepgramSTTService")
        except (ImportError, AttributeError) as e:
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

    logger.warning("Unsupported STT provider requested", provider=config.stt_provider)
    raise ValueError("Unsupported STT provider")


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
    provider = config.tts_provider
    fallback_provider_raw = app_settings.voice.tts_fallback_provider
    fallback_provider = (
        fallback_provider_raw if isinstance(fallback_provider_raw, str) else "none"
    )
    if fallback_provider not in {"none", "elevenlabs", "azure"}:
        fallback_provider = "none"

    try:
        return _create_tts_service_for_provider(provider, config)
    except (ImportError, ValueError) as primary_error:
        if fallback_provider not in {"", "none", provider}:
            logger.warning(
                "Primary TTS provider failed; attempting fallback",
                provider=provider,
                fallback_provider=fallback_provider,
                error_type=type(primary_error).__name__,
                error=str(primary_error),
            )
            try:
                return _create_tts_service_for_provider(fallback_provider, config)
            except Exception as fallback_error:
                raise RuntimeError(
                    "TTS setup failed for primary and fallback providers"
                ) from fallback_error
        raise


def _create_tts_service_for_provider(provider: str, config: VoiceAgentExtension) -> Any:
    if provider == "piper":
        voice_id = config.tts_voice_id
        try:
            piper_module = importlib.import_module("pipecat.services.piper.tts")
            PiperTTSService = getattr(piper_module, "PiperTTSService")
            PiperTTSSettings = getattr(piper_module, "PiperTTSSettings", None)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                "Piper TTS requires pipecat[piper]. "
                "Install with: pip install 'bindu[voice]'"
            ) from e

        if PiperTTSSettings is not None:
            tts = PiperTTSService(
                settings=PiperTTSSettings(
                    voice=voice_id,
                ),
                sample_rate=config.sample_rate,
            )
        else:
            tts = PiperTTSService(
                voice_id=voice_id,
                sample_rate=config.sample_rate,
            )

        logger.info(f"Created Piper TTS: voice={voice_id}")
        return tts

    if provider == "elevenlabs":
        api_key = app_settings.voice.tts_api_key
        if not api_key:
            logger.warning(
                "TTS service configuration incomplete: missing API key",
                setting="VOICE__TTS_API_KEY",
            )
            raise ValueError("TTS service configuration incomplete")

        try:
            elevenlabs_module = importlib.import_module(
                "pipecat.services.elevenlabs.tts"
            )
            ElevenLabsTTSService = getattr(elevenlabs_module, "ElevenLabsTTSService")
            ElevenLabsTTSSettings = getattr(
                elevenlabs_module, "ElevenLabsTTSSettings", None
            )
        except (ImportError, AttributeError) as e:
            raise ImportError(
                "ElevenLabs TTS requires pipecat[elevenlabs]. "
                "Install with: pip install 'bindu[voice]'"
            ) from e

        if ElevenLabsTTSSettings is not None:
            tts = ElevenLabsTTSService(
                api_key=api_key,
                settings=ElevenLabsTTSSettings(
                    voice=config.tts_voice_id,
                    model=config.tts_model,
                ),
            )
        else:
            tts = ElevenLabsTTSService(
                api_key=api_key,
                voice_id=config.tts_voice_id,
                model=config.tts_model,
            )
        logger.info(
            f"Created ElevenLabs TTS: voice={config.tts_voice_id}, model={config.tts_model}"
        )
        return tts

    if provider == "azure":
        azure_api_key = app_settings.voice.azure_tts_api_key
        azure_region = app_settings.voice.azure_tts_region
        azure_voice = app_settings.voice.azure_tts_voice or config.tts_voice_id
        if not azure_api_key:
            logger.warning(
                "Azure TTS configuration incomplete: missing API key",
                setting="VOICE__AZURE_TTS_API_KEY",
            )
            raise ValueError("Azure TTS configuration incomplete")
        if not azure_region:
            logger.warning(
                "Azure TTS configuration incomplete: missing region",
                setting="VOICE__AZURE_TTS_REGION",
            )
            raise ValueError("Azure TTS configuration incomplete")

        try:
            azure_module = importlib.import_module("pipecat.services.azure.tts")
            AzureTTSService = getattr(azure_module, "AzureTTSService")
            AzureTTSSettings = getattr(azure_module, "AzureTTSSettings", None)
        except (ImportError, AttributeError) as e:
            raise ImportError(
                "Azure TTS requires pipecat[azure]. "
                "Install with: pip install 'bindu[voice]'"
            ) from e

        if AzureTTSSettings is not None:
            tts = AzureTTSService(
                api_key=azure_api_key,
                region=azure_region,
                settings=AzureTTSSettings(voice=azure_voice),
                sample_rate=config.sample_rate,
            )
        else:
            tts = AzureTTSService(
                api_key=azure_api_key,
                region=azure_region,
                voice=azure_voice,
                sample_rate=config.sample_rate,
            )

        logger.info(f"Created Azure TTS: voice={azure_voice}, region={azure_region}")
        return tts

    logger.warning("Unsupported TTS provider requested", provider=provider)
    raise ValueError("Unsupported TTS provider")
