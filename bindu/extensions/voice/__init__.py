"""Voice Agent extension for real-time voice conversations.

Provides Vapi-like voice capabilities (STT → Agent → TTS) integrated
into Bindu's A2A protocol and extension system.

Usage::

    from bindu.extensions.voice import VoiceAgentExtension

    voice = VoiceAgentExtension(
        stt_provider="deepgram",
        tts_provider="elevenlabs",
        tts_voice_id="21m00Tcm4TlvDq8ikWAM",
    )
"""

from .voice_agent_extension import VoiceAgentExtension

__all__ = ["VoiceAgentExtension"]
