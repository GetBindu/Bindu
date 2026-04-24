#!/usr/bin/env bash
set -euo pipefail

# One-command smoke test for:
# 1) Deepgram STT key
# 2) TTS provider path (Piper / Azure / ElevenLabs)
# 3) Optional fallback provider check
# 4) Optional Bindu voice endpoint preflight
#
# Usage:
#   chmod +x scripts/test_voice_providers.sh
#   VOICE__STT_API_KEY=... VOICE__TTS_PROVIDER=piper TEST_WAV_PATH=/abs/path/test.wav scripts/test_voice_providers.sh
#
# Optional:
#   VOICE__TTS_PROVIDER=piper|azure|elevenlabs
#   VOICE__TTS_FALLBACK_PROVIDER=none|azure|elevenlabs
#   VOICE__TTS_VOICE_ID=<provider_voice_id>
#   BINDU_BASE_URL=http://localhost:3773
#   scripts/test_voice_providers.sh --bindu
#   scripts/test_voice_providers.sh --gen-sample
#   scripts/test_voice_providers.sh --save-artifacts
#   ARTIFACTS_DIR=./logs/voice-provider-tests scripts/test_voice_providers.sh --save-artifacts

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BINDU_CHECK=false
GENERATE_SAMPLE=false
SAVE_ARTIFACTS=false

for arg in "$@"; do
  case "$arg" in
    --bindu)
      BINDU_CHECK=true
      ;;
    --gen-sample)
      GENERATE_SAMPLE=true
      ;;
    --save-artifacts)
      SAVE_ARTIFACTS=true
      ;;
    *)
      ;;
  esac
done

VOICE_ID="${VOICE__TTS_VOICE_ID:-21m00Tcm4TlvDq8ikWAM}"
TTS_PROVIDER="${VOICE__TTS_PROVIDER:-elevenlabs}"
TTS_FALLBACK_PROVIDER="${VOICE__TTS_FALLBACK_PROVIDER:-none}"
BINDU_BASE_URL="${BINDU_BASE_URL:-http://localhost:3773}"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ARTIFACTS_ROOT="${ARTIFACTS_DIR:-./logs/voice-provider-tests}"
ARTIFACTS_RUN_DIR=""

pass() { echo -e "${GREEN}PASS${NC} - $1"; }
fail() { echo -e "${RED}FAIL${NC} - $1"; }
warn() { echo -e "${YELLOW}WARN${NC} - $1"; }

to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

require_env() {
  local key="$1"
  if [[ -z "${!key:-}" ]]; then
    fail "Missing env var: $key"
    return 1
  fi
  return 0
}

generate_sample_wav() {
  local out_path="$1"
  python3 - "$out_path" <<'PY'
import math
import struct
import sys
import wave

path = sys.argv[1]
sample_rate = 16000
duration_sec = 2.0
freq = 440.0
amplitude = 0.3

n_samples = int(sample_rate * duration_sec)
with wave.open(path, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    for i in range(n_samples):
        t = i / sample_rate
        value = int(32767 * amplitude * math.sin(2.0 * math.pi * freq * t))
        wf.writeframesraw(struct.pack("<h", value))
PY
}

save_artifacts() {
  [[ "$SAVE_ARTIFACTS" == true ]] || return 0

  local ts
  ts="$(date +%Y%m%d_%H%M%S)"
  ARTIFACTS_RUN_DIR="${ARTIFACTS_ROOT}/${ts}"

  mkdir -p "$ARTIFACTS_RUN_DIR"

  [[ -n "${DG_BODY:-}" && -f "$DG_BODY" ]] && cp "$DG_BODY" "$ARTIFACTS_RUN_DIR/deepgram.json"
  [[ -n "${EL_AUDIO:-}" && -f "$EL_AUDIO" ]] && cp "$EL_AUDIO" "$ARTIFACTS_RUN_DIR/elevenlabs.mp3"
  [[ -n "${EL_BODY:-}" && -f "$EL_BODY" ]] && cp "$EL_BODY" "$ARTIFACTS_RUN_DIR/elevenlabs_error.json"
  [[ -n "${AZ_BODY:-}" && -f "$AZ_BODY" ]] && cp "$AZ_BODY" "$ARTIFACTS_RUN_DIR/azure_voices.json"
  [[ -n "${AZ_ERR_BODY:-}" && -f "$AZ_ERR_BODY" ]] && cp "$AZ_ERR_BODY" "$ARTIFACTS_RUN_DIR/azure_error.json"
  [[ -n "${TEST_WAV_PATH:-}" && -f "$TEST_WAV_PATH" ]] && cp "$TEST_WAV_PATH" "$ARTIFACTS_RUN_DIR/test_input.wav"
  [[ -n "${HEALTH_BODY:-}" && -f "$HEALTH_BODY" ]] && cp "$HEALTH_BODY" "$ARTIFACTS_RUN_DIR/bindu_health.json"
  [[ -n "${SESSION_BODY:-}" && -f "$SESSION_BODY" ]] && cp "$SESSION_BODY" "$ARTIFACTS_RUN_DIR/bindu_session.json"

  pass "Saved artifacts to $ARTIFACTS_RUN_DIR"
}

echo "Running voice provider checks..."
echo "Primary TTS provider: ${TTS_PROVIDER}"
echo "Fallback TTS provider: ${TTS_FALLBACK_PROVIDER}"

# --- Validate inputs ---
input_ok=true
require_env "VOICE__STT_API_KEY" || input_ok=false

if [[ -z "${TEST_WAV_PATH:-}" ]]; then
  if [[ "$GENERATE_SAMPLE" == true ]]; then
    TEST_WAV_PATH="$TMP_DIR/sample.wav"
    if command -v python3 >/dev/null 2>&1; then
      generate_sample_wav "$TEST_WAV_PATH"
      pass "Generated sample WAV at $TEST_WAV_PATH"
    else
      fail "python3 is required for --gen-sample but was not found"
      input_ok=false
    fi
  else
    fail "Missing env var: TEST_WAV_PATH (absolute path to a short .wav file)"
    warn "Tip: pass --gen-sample to auto-generate a test WAV"
    input_ok=false
  fi
elif [[ ! -f "${TEST_WAV_PATH}" ]]; then
  fail "TEST_WAV_PATH does not exist: ${TEST_WAV_PATH}"
  input_ok=false
fi

if [[ "$input_ok" != true ]]; then
  echo ""
  echo "Example:"
  echo "VOICE__STT_API_KEY=... VOICE__TTS_PROVIDER=piper TEST_WAV_PATH=/abs/path/test.wav scripts/test_voice_providers.sh"
  echo "VOICE__STT_API_KEY=... VOICE__TTS_PROVIDER=piper scripts/test_voice_providers.sh --gen-sample"
  exit 1
fi

# --- Deepgram STT test ---
DG_BODY="$TMP_DIR/deepgram.json"
DG_HTTP=$(curl -sS -o "$DG_BODY" -w "%{http_code}" \
  "https://api.deepgram.com/v1/listen?model=nova-3&language=en" \
  -H "Authorization: Token ${VOICE__STT_API_KEY}" \
  -H "Content-Type: audio/wav" \
  --data-binary @"${TEST_WAV_PATH}" || true)

if [[ "$DG_HTTP" == "200" ]]; then
  if grep -qi '"transcript"' "$DG_BODY"; then
    pass "Deepgram API key works (HTTP 200, transcript present)"
  else
    warn "Deepgram returned 200 but transcript field not found"
    echo "Deepgram response snippet:"
    head -c 400 "$DG_BODY"; echo
  fi
else
  fail "Deepgram API check failed (HTTP $DG_HTTP)"
  echo "Deepgram response snippet:"
  head -c 400 "$DG_BODY"; echo
fi

check_elevenlabs_tts() {
  local provider_label="$1"

  if ! require_env "VOICE__TTS_API_KEY"; then
    return 1
  fi

  EL_AUDIO="$TMP_DIR/elevenlabs.mp3"
  EL_BODY="$TMP_DIR/elevenlabs.json"
  EL_HTTP=$(curl -sS -o "$EL_AUDIO" -w "%{http_code}" \
    -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
    -H "xi-api-key: ${VOICE__TTS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"text":"Hello from Bindu provider smoke test","model_id":"eleven_turbo_v2_5"}' || true)

  if [[ "$EL_HTTP" == "200" ]]; then
    SIZE=$(wc -c < "$EL_AUDIO" | tr -d ' ')
    if [[ "${SIZE}" -gt 1000 ]]; then
      pass "${provider_label}: ElevenLabs works (HTTP 200, audio ${SIZE} bytes)"
      return 0
    fi
    warn "${provider_label}: ElevenLabs returned 200 but audio looks too small (${SIZE} bytes)"
    return 0
  fi

  # On errors, ElevenLabs usually returns JSON. Re-run to capture body.
  curl -sS \
    -X POST "https://api.elevenlabs.io/v1/text-to-speech/${VOICE_ID}" \
    -H "xi-api-key: ${VOICE__TTS_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"text":"Hello from Bindu provider smoke test","model_id":"eleven_turbo_v2_5"}' \
    > "$EL_BODY" || true

  fail "${provider_label}: ElevenLabs check failed (HTTP $EL_HTTP)"
  echo "ElevenLabs response snippet:"
  head -c 400 "$EL_BODY"; echo
  return 1
}

check_azure_tts() {
  local provider_label="$1"

  if ! require_env "VOICE__AZURE_TTS_API_KEY"; then
    return 1
  fi
  if ! require_env "VOICE__AZURE_TTS_REGION"; then
    return 1
  fi

  AZ_BODY="$TMP_DIR/azure_voices.json"
  AZ_ERR_BODY="$TMP_DIR/azure_error.json"
  local azure_url="https://${VOICE__AZURE_TTS_REGION}.tts.speech.microsoft.com/cognitiveservices/voices/list"
  local az_http
  az_http=$(curl -sS -o "$AZ_BODY" -w "%{http_code}" \
    "$azure_url" \
    -H "Ocp-Apim-Subscription-Key: ${VOICE__AZURE_TTS_API_KEY}" || true)

  if [[ "$az_http" == "200" ]]; then
    if grep -q '"ShortName"' "$AZ_BODY"; then
      pass "${provider_label}: Azure Speech credentials work (HTTP 200, voices listed)"
      return 0
    fi
    warn "${provider_label}: Azure returned 200 but voice list format was unexpected"
    return 0
  fi

  cp "$AZ_BODY" "$AZ_ERR_BODY" 2>/dev/null || true
  fail "${provider_label}: Azure Speech check failed (HTTP $az_http)"
  echo "Azure response snippet:"
  head -c 400 "$AZ_ERR_BODY"; echo
  return 1
}

check_piper_tts() {
  local provider_label="$1"

  if ! command -v python3 >/dev/null 2>&1; then
    fail "${provider_label}: python3 is required to validate Piper dependency"
    return 1
  fi

  if python3 - <<'PY'
import importlib
importlib.import_module("pipecat.services.piper.tts")
print("ok")
PY
  then
    pass "${provider_label}: Piper dependency is available"
    return 0
  fi

  fail "${provider_label}: Piper dependency missing (install pipecat-ai[piper])"
  return 1
}

check_tts_provider() {
  local provider_raw="$1"
  local provider_label="$2"
  local provider
  provider="$(to_lower "$provider_raw")"

  case "$provider" in
    elevenlabs)
      check_elevenlabs_tts "$provider_label"
      ;;
    azure)
      check_azure_tts "$provider_label"
      ;;
    piper)
      check_piper_tts "$provider_label"
      ;;
    none|"")
      warn "${provider_label}: no provider configured"
      ;;
    *)
      fail "${provider_label}: unsupported provider '$provider_raw'"
      return 1
      ;;
  esac
}

echo ""
echo "Running TTS provider checks..."
check_tts_provider "$TTS_PROVIDER" "Primary TTS"
if [[ "$(to_lower "$TTS_FALLBACK_PROVIDER")" != "none" && -n "${TTS_FALLBACK_PROVIDER}" ]]; then
  check_tts_provider "$TTS_FALLBACK_PROVIDER" "Fallback TTS"
fi

# --- Optional Bindu integration test ---
if [[ "$BINDU_CHECK" == true ]]; then
  echo ""
  echo "Running Bindu endpoint checks at ${BINDU_BASE_URL} ..."

  HEALTH_BODY="$TMP_DIR/health.json"
  HEALTH_HTTP=$(curl -sS -o "$HEALTH_BODY" -w "%{http_code}" "${BINDU_BASE_URL}/health" || true)

  if [[ "$HEALTH_HTTP" == "200" ]]; then
    pass "Bindu health endpoint reachable"
  else
    fail "Bindu health endpoint failed (HTTP $HEALTH_HTTP)"
    head -c 300 "$HEALTH_BODY"; echo
  fi

  SESSION_BODY="$TMP_DIR/session.json"
  SESSION_HTTP=$(curl -sS -o "$SESSION_BODY" -w "%{http_code}" \
    -X POST "${BINDU_BASE_URL}/voice/session/start" \
    -H "Content-Type: application/json" \
    -d '{}' || true)

  if [[ "$SESSION_HTTP" == "201" ]]; then
    if grep -q '"ws_url"' "$SESSION_BODY"; then
      pass "Bindu voice session start works (HTTP 201, ws_url returned)"
    else
      warn "Voice session created but ws_url field missing"
      head -c 400 "$SESSION_BODY"; echo
    fi
  else
    fail "Bindu voice session start failed (HTTP $SESSION_HTTP)"
    head -c 400 "$SESSION_BODY"; echo
  fi
fi

save_artifacts

echo ""
echo "Done."
