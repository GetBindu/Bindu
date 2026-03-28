"""Unit tests for VoiceAgentExtension."""

import pytest

from bindu.extensions.voice.voice_agent_extension import VoiceAgentExtension


class TestVoiceAgentExtensionCreation:
    """Test VoiceAgentExtension construction and defaults."""

    def test_default_creation(self):
        ext = VoiceAgentExtension()
        assert ext.stt_provider == "deepgram"
        assert ext.stt_model == "nova-3"
        assert ext.stt_language == "en"
        assert ext.tts_provider == "elevenlabs"
        assert ext.tts_voice_id == "21m00Tcm4TlvDq8ikWAM"
        assert ext.tts_model == "eleven_turbo_v2_5"
        assert ext.sample_rate == 16000
        assert ext.allow_interruptions is True
        assert ext.vad_enabled is True

    def test_custom_creation(self):
        ext = VoiceAgentExtension(
            stt_provider="deepgram",
            stt_model="nova-2",
            stt_language="es",
            tts_provider="elevenlabs",
            tts_voice_id="custom-voice",
            tts_model="eleven_turbo_v2",
            sample_rate=24000,
            allow_interruptions=False,
            vad_enabled=False,
            description="My voice agent",
        )
        assert ext.stt_model == "nova-2"
        assert ext.stt_language == "es"
        assert ext.tts_voice_id == "custom-voice"
        assert ext.sample_rate == 24000
        assert ext.allow_interruptions is False
        assert ext.vad_enabled is False

    def test_invalid_sample_rate_low(self):
        with pytest.raises(ValueError, match="Sample rate must be between"):
            VoiceAgentExtension(sample_rate=4000)

    def test_invalid_sample_rate_high(self):
        with pytest.raises(ValueError, match="Sample rate must be between"):
            VoiceAgentExtension(sample_rate=100000)


class TestVoiceAgentExtensionAgentCard:
    """Test agent_extension property for agent card."""

    def test_agent_extension_returns_agent_extension(self):
        ext = VoiceAgentExtension()
        ae = ext.agent_extension
        assert "uri" in ae
        assert "voice" in ae["uri"]
        assert ae["required"] is False

    def test_agent_extension_params(self):
        ext = VoiceAgentExtension(
            stt_provider="deepgram",
            tts_provider="elevenlabs",
            sample_rate=16000,
            allow_interruptions=True,
        )
        ae = ext.agent_extension
        params = ae["params"]
        assert params["stt_provider"] == "deepgram"
        assert params["tts_provider"] == "elevenlabs"
        assert params["sample_rate"] == 16000
        assert params["allow_interruptions"] is True

    def test_agent_extension_cached(self):
        ext = VoiceAgentExtension()
        ae1 = ext.agent_extension
        ae2 = ext.agent_extension
        assert ae1 is ae2

    def test_custom_description(self):
        ext = VoiceAgentExtension(description="Custom desc")
        ae = ext.agent_extension
        assert ae["description"] == "Custom desc"


class TestVoiceAgentExtensionSerialization:
    """Test to_dict and __repr__."""

    def test_to_dict(self):
        ext = VoiceAgentExtension()
        d = ext.to_dict()
        assert d["stt_provider"] == "deepgram"
        assert d["tts_provider"] == "elevenlabs"
        assert d["sample_rate"] == 16000
        assert "allow_interruptions" in d
        assert "vad_enabled" in d

    def test_repr(self):
        ext = VoiceAgentExtension()
        r = repr(ext)
        assert "VoiceAgentExtension" in r
        assert "deepgram" in r
        assert "nova-3" in r
