"""Unit tests for voice service factory."""

import pytest
from unittest.mock import patch, MagicMock

from bindu.extensions.voice.service_factory import (
    create_stt_service,
    create_tts_service,
)
from bindu.extensions.voice import VoiceAgentExtension


class TestCreateSTTService:
    """Test STT service creation."""

    def test_missing_api_key_raises(self):
        ext = VoiceAgentExtension()
        with patch(
            "bindu.extensions.voice.service_factory.app_settings"
        ) as mock_settings:
            mock_settings.voice.stt_api_key = ""
            with pytest.raises(
                ValueError, match="STT service configuration incomplete"
            ):
                create_stt_service(ext)

    def test_unsupported_provider_raises(self):
        ext = VoiceAgentExtension(stt_provider="unknown_provider")
        with patch(
            "bindu.extensions.voice.service_factory.app_settings"
        ) as mock_settings:
            mock_settings.voice.stt_api_key = (
                "unit-test-stt-token"  # pragma: allowlist secret
            )
            with pytest.raises(ValueError, match="Unsupported STT provider"):
                create_stt_service(ext)

    def test_deepgram_creation(self):
        ext = VoiceAgentExtension(stt_provider="deepgram", stt_model="nova-3")
        mock_stt_cls = MagicMock()
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.deepgram.stt": MagicMock(
                        DeepgramSTTService=mock_stt_cls
                    )
                },
            ),
        ):
            mock_settings.voice.stt_api_key = (
                "unit-test-stt-token"  # pragma: allowlist secret
            )
            result = create_stt_service(ext)
            mock_stt_cls.assert_called_once_with(
                api_key="unit-test-stt-token",  # pragma: allowlist secret
                model="nova-3",
                language="en",
            )
            assert result == mock_stt_cls.return_value


class TestCreateTTSService:
    """Test TTS service creation."""

    def test_missing_api_key_raises(self):
        ext = VoiceAgentExtension()
        with patch(
            "bindu.extensions.voice.service_factory.app_settings"
        ) as mock_settings:
            mock_settings.voice.tts_api_key = ""
            with pytest.raises(
                ValueError, match="TTS service configuration incomplete"
            ):
                create_tts_service(ext)

    def test_unsupported_provider_raises(self):
        ext = VoiceAgentExtension(tts_provider="unknown_tts")
        with patch(
            "bindu.extensions.voice.service_factory.app_settings"
        ) as mock_settings:
            mock_settings.voice.tts_api_key = (
                "unit-test-tts-token"  # pragma: allowlist secret
            )
            with pytest.raises(ValueError, match="Unsupported TTS provider"):
                create_tts_service(ext)

    def test_elevenlabs_creation(self):
        ext = VoiceAgentExtension(
            tts_provider="elevenlabs",
            tts_voice_id="voice-abc",
            tts_model="eleven_turbo_v2_5",
        )
        mock_tts_cls = MagicMock()
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.elevenlabs.tts": MagicMock(
                        ElevenLabsTTSService=mock_tts_cls
                    )
                },
            ),
        ):
            mock_settings.voice.tts_api_key = (
                "unit-test-tts-token"  # pragma: allowlist secret
            )
            result = create_tts_service(ext)
            mock_tts_cls.assert_called_once_with(
                api_key="unit-test-tts-token",  # pragma: allowlist secret
                voice_id="voice-abc",
                model="eleven_turbo_v2_5",
            )
            assert result == mock_tts_cls.return_value
