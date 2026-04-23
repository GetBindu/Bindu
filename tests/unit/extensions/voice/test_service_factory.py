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
        mock_tts_settings = MagicMock()
        mock_tts_cls.Settings = mock_tts_settings
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.elevenlabs.tts": MagicMock(
                        ElevenLabsTTSService=mock_tts_cls,
                    )
                },
            ),
        ):
            mock_settings.voice.tts_api_key = (
                "unit-test-tts-token"  # pragma: allowlist secret
            )
            result = create_tts_service(ext)
            mock_tts_settings.assert_called_once_with(
                voice="voice-abc",
                model="eleven_turbo_v2_5",
            )
            mock_tts_cls.assert_called_once_with(
                api_key="unit-test-tts-token",  # pragma: allowlist secret
                settings=mock_tts_settings.return_value,
            )
            assert result == mock_tts_cls.return_value

    def test_piper_creation_without_api_key(self):
        ext = VoiceAgentExtension(
            tts_provider="piper",
            tts_voice_id="en_US-ryan-high",
        )
        mock_tts_cls = MagicMock()
        mock_tts_settings = MagicMock()
        mock_tts_cls.Settings = mock_tts_settings
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.piper.tts": MagicMock(
                        PiperTTSService=mock_tts_cls,
                    )
                },
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "unexpected-provider"
            result = create_tts_service(ext)
            mock_tts_settings.assert_called_once_with(voice="en_US-ryan-high")
            mock_tts_cls.assert_called_once_with(
                settings=mock_tts_settings.return_value,
                sample_rate=16000,
            )
            assert result == mock_tts_cls.return_value

    def test_piper_missing_nested_settings_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="piper", tts_voice_id="en_US-ryan-high")
        mock_tts_cls = MagicMock()
        del mock_tts_cls.Settings
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.piper.tts": MagicMock(
                        PiperTTSService=mock_tts_cls,
                    )
                },
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "none"

            with pytest.raises(
                ImportError, match="Piper TTS requires a nested Settings class"
            ):
                create_tts_service(ext)

    def test_piper_import_error_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="piper", tts_voice_id="en_US-ryan-high")
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch(
                "bindu.extensions.voice.service_factory.importlib.import_module",
                side_effect=ImportError("missing piper"),
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "none"

            with pytest.raises(
                ImportError, match=r"Piper TTS requires pipecat\[piper\]"
            ):
                create_tts_service(ext)

    def test_elevenlabs_import_error_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="elevenlabs", tts_voice_id="voice-abc")
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch(
                "bindu.extensions.voice.service_factory.importlib.import_module",
                side_effect=ImportError("missing elevenlabs"),
            ),
        ):
            mock_settings.voice.tts_api_key = (
                "unit-test-tts-token"  # pragma: allowlist secret
            )
            mock_settings.voice.tts_fallback_provider = "none"

            with pytest.raises(
                ImportError, match=r"ElevenLabs TTS requires pipecat\[elevenlabs\]"
            ):
                create_tts_service(ext)

    def test_elevenlabs_missing_nested_settings_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="elevenlabs", tts_voice_id="voice-abc")
        mock_tts_cls = MagicMock()
        del mock_tts_cls.Settings
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
            mock_settings.voice.tts_fallback_provider = "none"

            with pytest.raises(
                ImportError, match="ElevenLabs TTS requires a nested Settings class"
            ):
                create_tts_service(ext)

    def test_azure_import_error_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="azure", tts_voice_id="en-US-SaraNeural")
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch(
                "bindu.extensions.voice.service_factory.importlib.import_module",
                side_effect=ImportError("missing azure"),
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "none"
            mock_settings.voice.azure_tts_api_key = (
                "unit-test-azure-token"  # pragma: allowlist secret
            )
            mock_settings.voice.azure_tts_region = "eastus"
            mock_settings.voice.azure_tts_voice = "en-US-SaraNeural"

            with pytest.raises(
                ImportError, match=r"Azure TTS requires pipecat\[azure\]"
            ):
                create_tts_service(ext)

    def test_azure_missing_nested_settings_raises_importerror(self):
        ext = VoiceAgentExtension(tts_provider="azure", tts_voice_id="en-US-SaraNeural")
        mock_tts_cls = MagicMock()
        del mock_tts_cls.Settings
        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.azure.tts": MagicMock(AzureTTSService=mock_tts_cls)
                },
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "none"
            mock_settings.voice.azure_tts_api_key = (
                "unit-test-azure-token"  # pragma: allowlist secret
            )
            mock_settings.voice.azure_tts_region = "eastus"
            mock_settings.voice.azure_tts_voice = "en-US-SaraNeural"

            with pytest.raises(
                ImportError, match="Azure TTS requires a nested Settings class"
            ):
                create_tts_service(ext)

    def test_azure_fallback_when_elevenlabs_fails(self):
        ext = VoiceAgentExtension(
            tts_provider="elevenlabs",
            tts_voice_id="en-US-SaraNeural",
        )
        mock_azure_cls = MagicMock()
        mock_azure_settings = MagicMock()
        mock_azure_cls.Settings = mock_azure_settings
        mock_elevenlabs_cls = MagicMock()

        with (
            patch(
                "bindu.extensions.voice.service_factory.app_settings"
            ) as mock_settings,
            patch.dict(
                "sys.modules",
                {
                    "pipecat.services.elevenlabs.tts": MagicMock(
                        ElevenLabsTTSService=mock_elevenlabs_cls,
                    ),
                    "pipecat.services.azure.tts": MagicMock(
                        AzureTTSService=mock_azure_cls,
                    ),
                },
            ),
        ):
            mock_settings.voice.tts_api_key = ""
            mock_settings.voice.tts_fallback_provider = "azure"
            mock_settings.voice.azure_tts_api_key = (
                "unit-test-azure-token"  # pragma: allowlist secret
            )
            mock_settings.voice.azure_tts_region = "eastus"
            mock_settings.voice.azure_tts_voice = "en-US-SaraNeural"

            result = create_tts_service(ext)

            mock_azure_settings.assert_called_once_with(voice="en-US-SaraNeural")
            mock_azure_cls.assert_called_once_with(
                api_key="unit-test-azure-token",  # pragma: allowlist secret
                region="eastus",
                settings=mock_azure_settings.return_value,
                sample_rate=16000,
            )
            assert result == mock_azure_cls.return_value
