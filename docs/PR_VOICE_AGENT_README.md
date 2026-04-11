# Voice Agent Extension — Progress & Documentation PR

## Overview
This PR introduces the initial implementation of the Voice Agent Extension for Bindu, enabling real-time voice conversations between users and agents. The extension integrates backend, frontend, and testing components, following the architecture and plan outlined in `docs/VOICE_AGENT_PLAN.md`.

---

## What’s Included

### Backend
- **New voice extension module**: `bindu/extensions/voice/` with:
  - `__init__.py`, `voice_agent_extension.py`, `service_factory.py`, `pipeline_builder.py`, `session_manager.py`, `agent_bridge.py`, `audio_config.py`
- **Endpoints**: `bindu/server/endpoints/voice_endpoints.py` (REST + WebSocket)
- **Settings**: `bindu/settings.py` updated with `VoiceSettings`
- **App integration**: `bindu/server/applications.py` updated for conditional voice route registration and session manager
- **Capabilities**: `bindu/utils/capabilities.py` updated for voice extension helpers
- **Penguin integration**: `bindu/penguin/bindufy.py` updated to accept voice config and add the extension

### Frontend
- **Voice UI and client**:
  - `frontend/src/lib/services/voice-client.ts`: WebSocket client, audio capture/playback
  - `frontend/src/lib/stores/voice.ts`: Svelte stores for voice state and transcripts
  - `frontend/src/lib/components/voice/VoiceCallPanel.svelte`, `VoiceCallButton.svelte`, `LiveTranscript.svelte`: UI components for voice session
- **Integration**: Existing chat and agent message handler files updated for voice support

### Tests
- **Unit tests** for all major backend components:
  - `tests/unit/extensions/voice/test_voice_extension.py`
  - `tests/unit/extensions/voice/test_session_manager.py`
  - `tests/unit/extensions/voice/test_service_factory.py`
  - `tests/unit/extensions/voice/test_agent_bridge.py`
  - `tests/unit/extensions/voice/test_voice_endpoints.py`

### Examples & Docs
- **Example agent**: `examples/voice-agent/main.py`, `.env.example`, and `README.md`
- **Plan**: `docs/VOICE_AGENT_PLAN.md` (implementation plan)

---

## Current Progress
- All major backend, frontend, and test files are present and staged.
- Integration into the main app and settings is in progress.
- Endpoints and frontend integration are actively being refined.
- Unit tests for the extension and its components are included.
- Example agent and configuration are provided.
- Documentation plan is present; full user-facing docs (`docs/VOICE.md`) are planned.

---

## How to Test
1. **Install dependencies**:
   - Ensure `pipecat-ai[deepgram,elevenlabs,silero]` and `websockets` are installed (see `pyproject.toml` voice group).
2. **Set environment variables**:
   - `VOICE__STT_API_KEY`, `VOICE__TTS_API_KEY` (see `.env.example`)
3. **Run backend tests**:
   - `uv run pytest tests/unit/extensions/voice/ -v`
4. **Run frontend**:
   - Start the Svelte frontend and verify the voice call UI appears for voice-enabled agents.
5. **Manual E2E**:
   - Start a voice session from the UI, speak, and verify agent responses and transcripts.
6. **Check task persistence**:
   - After a session, verify conversation history via `GET /tasks/get`.

---

## Next Steps & Improvements
- [ ] Complete and verify all items in the implementation plan checklist (see `docs/VOICE_AGENT_PLAN.md`)
- [ ] Finalize and publish user documentation (`docs/VOICE.md`)
- [ ] Polish frontend UI/UX and error handling
- [ ] Expand test coverage (integration, E2E, edge cases)
- [ ] Lint and format: `uv run pre-commit run --all-files`
- [ ] Optimize session cleanup and resource management
- [ ] Add more example agents and configuration scenarios
- [ ] Prepare for future extensions (telephony, WebRTC, multi-language, etc.)

---

## References
- [VOICE_AGENT_PLAN.md](VOICE_AGENT_PLAN.md)
- [dograh-hq/dograh](https://github.com/dograh-hq/dograh)
- [pipecat-ai/pipecat-examples](https://github.com/pipecat-ai/pipecat-examples)

---

**Contributors:**
- @Co-vengers

---

For questions or feedback, please comment on this PR.
