"""Voice pipeline builder.

Assembles a pipecat-compatible voice pipeline:
    WebSocket input → STT → Agent Bridge → TTS → WebSocket output

The pipeline is built lazily when starting a voice session.
"""

from __future__ import annotations

from typing import Any, Callable

from bindu.utils.logging import get_logger

from .agent_bridge import AgentBridgeProcessor
from .service_factory import create_stt_service, create_tts_service
from .voice_agent_extension import VoiceAgentExtension

logger = get_logger("bindu.voice.pipeline_builder")


async def build_voice_pipeline(
    voice_ext: VoiceAgentExtension,
    manifest_run: Callable[..., Any],
    context_id: str,
    *,
    on_user_transcript: Callable[[str], Any] | None = None,
    on_agent_response: Callable[[str], Any] | None = None,
) -> dict[str, Any]:
    """Build the voice pipeline components.

    Returns a dict of pipeline components that can be wired up to a
    WebSocket transport. This keeps the pipeline builder independent
    of the specific pipecat transport implementation.

    Args:
        voice_ext: Voice agent extension with STT/TTS config.
        manifest_run: The agent manifest's ``run`` callable.
        context_id: A2A context ID for this session.
        on_user_transcript: Optional callback for user transcript events.
        on_agent_response: Optional callback for agent response events.

    Returns:
        Dictionary with ``stt``, ``tts``, and ``bridge`` components.
    """
    stt = create_stt_service(voice_ext)
    tts = create_tts_service(voice_ext)

    bridge = AgentBridgeProcessor(
        manifest_run=manifest_run,
        context_id=context_id,
        on_user_transcript=on_user_transcript,
        on_agent_response=on_agent_response,
    )

    logger.info(
        f"Voice pipeline built: STT={voice_ext.stt_provider}/{voice_ext.stt_model}, "
        f"TTS={voice_ext.tts_provider}/{voice_ext.tts_voice_id}, "
        f"context={context_id}"
    )

    return {
        "stt": stt,
        "tts": tts,
        "bridge": bridge,
    }
