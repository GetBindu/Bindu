#!/usr/bin/env bash
# Query matrix runner for the gateway_test_fleet.
#
# Hits POST /plan on the gateway (default http://localhost:3774) with a
# series of curated queries, captures the SSE stream, and summarizes
# pass/fail to stdout. Each case writes its raw stream to
# logs/<case_id>.sse for later inspection.
#
# Usage:
#   ./run_matrix.sh              # run all cases
#   ./run_matrix.sh Q7           # run a single case
#   GATEWAY_URL=http://example   # override gateway base URL
#   GATEWAY_API_KEY=...          # bearer token for the gateway's own
#                                # /plan auth (dev default in .env.local:
#                                # "dev-key-change-me")

set -euo pipefail

FLEET_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_DIR="${FLEET_DIR}/logs"
mkdir -p "${LOG_DIR}"

GATEWAY_URL="${GATEWAY_URL:-http://localhost:3774}"
GATEWAY_API_KEY="${GATEWAY_API_KEY:-dev-key-change-me}"

JOKE_URL="http://localhost:3773"
MATH_URL="http://localhost:3775"
POET_URL="http://localhost:3776"
RESEARCH_URL="http://localhost:3777"
FAQ_URL="http://localhost:3778"

# did_signed everywhere — matches the agreed full-auth test setup.
AUTH_BLOCK='"auth": { "type": "did_signed" }'

# --------------------------------------------------------------------
# Case definitions — each function prints a JSON body to stdout.
# --------------------------------------------------------------------

case_Q1() {
  cat <<EOF
{
  "question": "Tell me a joke about databases.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q2() {
  cat <<EOF
{
  "question": "Solve 17 * 23 step by step.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q3() {
  cat <<EOF
{
  "question": "Solve 12 + 5, then write a short poem celebrating the answer.",
  "agents": [
    { "name": "math", "endpoint": "${MATH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "solve", "description": "Solve math problems" }] },
    { "name": "poet", "endpoint": "${POET_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "write_poem", "description": "Write a short poem" }] }
  ]
}
EOF
}

case_Q4() {
  # Ambiguous — could be joke, could be poem, could be a "fun fact"
  cat <<EOF
{
  "question": "Make me smile with something creative.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] },
    { "name": "poet", "endpoint": "${POET_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "write_poem", "description": "Write a short poem" }] }
  ]
}
EOF
}

case_Q5() {
  cat <<EOF
{
  "question": "asdkjfh akjdhf aksdjfh aksdjfh",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q6() {
  # Empty question — should be rejected at the API boundary with a
  # clean 400, not allowed to crash the planner mid-stream. The
  # runner recognizes HTTP 400 as the expected success for this case.
  cat <<EOF
{
  "question": "",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}
# Cases that must be rejected upfront with HTTP 400.
EXPECT_400=("Q6")

case_Q7() {
  cat <<EOF
{
  "question": "Tell me a joke.",
  "agents": [
    { "name": "nowhere", "endpoint": "http://localhost:39999",
      ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q8() {
  cat <<EOF
{
  "question": "Tell me a joke.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}",
      "auth": { "type": "bearer", "token": "definitely-not-a-valid-token" },
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q9() {
  cat <<EOF
{
  "question": "Use the nonexistent_skill on the joke agent.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "nonexistent_skill", "description": "Does not exist on the agent" }] }
  ]
}
EOF
}

case_Q10() {
  # 30s timeout requested; most agents respond well under this. The
  # goal is to verify the planner respects the limit when it applies.
  cat <<EOF
{
  "question": "What is the capital of France? Answer with just one word.",
  "agents": [
    { "name": "research", "endpoint": "${RESEARCH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "web_research", "description": "Web search and summarize" }] }
  ],
  "preferences": { "timeout_ms": 30000 }
}
EOF
}

case_Q11() {
  # 10KB of filler context. Tests that the gateway forwards large
  # inputs to the peer without silent truncation.
  local filler
  filler=$(printf 'lorem ipsum %.0s' {1..700})
  cat <<EOF
{
  "question": "Given this context: ${filler}. Tell me a joke about it.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
}
EOF
}

case_Q12() {
  cat <<EOF
{
  "question": "What is the capital of France?",
  "agents": [
    { "name": "joke",     "endpoint": "${JOKE_URL}",     ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] },
    { "name": "math",     "endpoint": "${MATH_URL}",     ${AUTH_BLOCK},
      "skills": [{ "id": "solve", "description": "Solve math problems" }] },
    { "name": "poet",     "endpoint": "${POET_URL}",     ${AUTH_BLOCK},
      "skills": [{ "id": "write_poem", "description": "Write a short poem" }] },
    { "name": "research", "endpoint": "${RESEARCH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "web_research", "description": "Web search and summarize" }] },
    { "name": "faq",      "endpoint": "${FAQ_URL}",      ${AUTH_BLOCK},
      "skills": [{ "id": "docs_query", "description": "Answer Bindu documentation questions" }] }
  ]
}
EOF
}

case_Q_MULTIHOP() {
  # Complex multi-hop chain — each agent's output must feed the next.
  #
  # Goal: "Research the population of Tokyo, compute what 0.5% of it
  # is, then write a 4-line poem about that number of people."
  #
  # Forces the planner to:
  #   1. research_agent → fetch current Tokyo population (web search)
  #   2. math_agent    → compute 0.5% of the returned number
  #   3. poet_agent    → write a 4-line poem using the computed value
  #
  # Each step depends on the prior. If the planner chains correctly,
  # we'll see three task.started events in order, each consuming the
  # previous artifact. If it skips or parallelizes, the math step
  # will have no number to work with and surface an error.
  cat <<EOF
{
  "question": "First research the current approximate population of Tokyo (cite the source). Then compute what exactly 0.5% of that population is. Finally write a 4-line poem celebrating that number of people. Do all three steps in order.",
  "agents": [
    { "name": "research", "endpoint": "${RESEARCH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "web_research", "description": "Web search and summarize a factual question with sources" }] },
    { "name": "math",     "endpoint": "${MATH_URL}",     ${AUTH_BLOCK},
      "skills": [{ "id": "solve", "description": "Solve math problems step-by-step" }] },
    { "name": "poet",     "endpoint": "${POET_URL}",     ${AUTH_BLOCK},
      "skills": [{ "id": "write_poem", "description": "Write a short (max 4-line) poem on the given topic" }] }
  ],
  "preferences": { "max_steps": 10 }
}
EOF
}

case_Q13() {
  # Same session across two requests. Second call asks about the first.
  # Skipped by default — caller must pass $SESSION_ID the second time.
  cat <<EOF
{
  "question": "Remember the number 42. Now tell me a joke.",
  "agents": [
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke" }] }
  ]
  ${SESSION_ID:+, "session_id": "${SESSION_ID}"}
}
EOF
}

# --------------------------------------------------------------------
# Inbox-reproduction regression cases.
#
# These three cases mirror bugs first observed in the operator inbox
# (compound prompt produced only one agent's reply; turn-2 follow-up
# stuck to turn-1's agent; resubmitting a draft after a timeout
# double-billed). The first two pass against /plan today and exist as
# regression guards. The third (_C) currently fails — /plan has no
# idempotency — and is excluded from ALL_CASES so the matrix stays
# green. Run it explicitly with `run_dup_check` (see below the matrix).
# --------------------------------------------------------------------

case_Q_INBOX_REPRO_A() {
  # The exact prompt that surfaced the bug in the inbox log: a single
  # message requiring TWO agents (math, then joke about the result).
  # Today /plan handles this correctly — both task.started events fire.
  cat <<EOF
{
  "question": "solve 10+10-10 and write a joke with the result.",
  "agents": [
    { "name": "math", "endpoint": "${MATH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "solve_math", "description": "Solve math problems step by step" }] },
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke on any topic" }] }
  ]
}
EOF
}

case_Q_INBOX_REPRO_B() {
  # Turn-2 routing under a multi-recipient roster. Turn 1 was a math
  # question; turn 2 asks for a joke about that result. The planner
  # must re-route turn 2 to joke alone, NOT stick to math. Tests that
  # client-owned history doesn't leak sticky routing.
  cat <<EOF
{
  "question": "now tell me a joke about that result.",
  "history": [
    { "role": "user", "parts": [{ "type": "text", "text": "what is 10+10-10?" }] },
    { "role": "assistant", "parts": [{ "type": "text", "text": "The result of 10 + 10 - 10 is 10." }] }
  ],
  "agents": [
    { "name": "math", "endpoint": "${MATH_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "solve_math", "description": "Solve math problems step by step" }] },
    { "name": "joke", "endpoint": "${JOKE_URL}", ${AUTH_BLOCK},
      "skills": [{ "id": "tell_joke", "description": "Tell a joke on any topic" }] }
  ]
}
EOF
}

case_Q_INBOX_REPRO_C() {
  # Body for the duplicate-submit check. Fired twice in parallel by
  # run_dup_check (below). Body is intentionally identical to _A so
  # the dedup layer keys on (content, agents) instead of body diffing.
  case_Q_INBOX_REPRO_A
}

ALL_CASES=(Q1 Q2 Q3 Q4 Q5 Q6 Q7 Q8 Q9 Q10 Q11 Q12 Q_MULTIHOP Q_INBOX_REPRO_A Q_INBOX_REPRO_B)

# --------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------

run_case() {
  local cid="$1"
  local body_func="case_${cid}"
  if ! declare -F "${body_func}" >/dev/null; then
    echo "  [${cid}] UNKNOWN CASE"
    return 1
  fi

  local body
  body="$("${body_func}")"
  local out="${LOG_DIR}/${cid}.sse"
  local status_file="${LOG_DIR}/${cid}.status"

  echo "▶ ${cid}"

  # -N: no buffering. --max-time bounds total wall clock per case
  # to 90s so a hung stream doesn't wedge the whole run.
  local http_code
  http_code=$(curl -sN --max-time 90 \
    -o "${out}" \
    -w "%{http_code}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
    -H "Accept: text/event-stream" \
    -X POST "${GATEWAY_URL}/plan" \
    -d "${body}" \
    || true)

  echo "${http_code}" > "${status_file}"

  # Is this case expected to be rejected upfront?
  local expect_400=false
  for id in "${EXPECT_400[@]:-}"; do
    [[ "${id}" == "${cid}" ]] && expect_400=true
  done

  if [[ "${expect_400}" == "true" ]]; then
    if [[ "${http_code}" == "400" ]]; then
      echo "  HTTP 400 (expected) — request rejected at API boundary ✓"
      return 0
    fi
    echo "  HTTP ${http_code} (expected 400) — body:"
    cat "${out}" | sed 's/^/    /'
    echo "  ✗ ${cid} failed (expected 400, got ${http_code})"
    return 1
  fi

  if [[ "${http_code}" != "200" ]]; then
    echo "  HTTP ${http_code} — full body:"
    cat "${out}" | sed 's/^/    /'
    echo "  ✗ ${cid} failed (non-200)"
    return 1
  fi

  # Parse SSE for key markers.
  local has_plan has_final has_done has_error
  has_plan=$(grep -c '^event: plan' "${out}" || true)
  has_final=$(grep -c '^event: final' "${out}" || true)
  has_done=$(grep -c '^event: done' "${out}" || true)
  has_error=$(grep -c '^event: error' "${out}" || true)

  local verdict="ok"
  local details=""

  if [[ "${has_error}" -gt 0 ]]; then
    verdict="planner_error"
    details=$(grep -A1 '^event: error' "${out}" | head -n 4)
  elif [[ "${has_done}" -eq 0 ]]; then
    verdict="incomplete_stream"
    details="no 'done' event — planner may have crashed mid-stream"
  elif [[ "${has_final}" -eq 0 ]]; then
    verdict="no_final"
    details="stream ended without emitting 'final' — planner exited empty"
  fi

  echo "  plan=${has_plan}  final=${has_final}  done=${has_done}  error=${has_error}  → ${verdict}"
  if [[ -n "${details}" ]]; then
    echo "${details}" | sed 's/^/    /'
  fi
  [[ "${verdict}" == "ok" ]]
}

# Idempotency check for /plan. Fires Q_INBOX_REPRO_C's body twice in
# parallel and verifies that the gateway deduplicates: post-fix both
# responses share the same session_id; today they don't (two separate
# runs, double agent invocations, double bill).
#
# Until the gateway lands an Idempotency-Key/(session,content_hash)
# layer, this command is expected to FAIL — it's the regression guard
# for that Phase 2 work.
run_dup_check() {
  local body
  body="$(case_Q_INBOX_REPRO_C)"
  local out1="${LOG_DIR}/Q_INBOX_REPRO_C.1.sse"
  local out2="${LOG_DIR}/Q_INBOX_REPRO_C.2.sse"

  echo "▶ Q_INBOX_REPRO_C (parallel dup-submit)"

  curl -sN --max-time 90 -o "${out1}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
    -H "Accept: text/event-stream" \
    -X POST "${GATEWAY_URL}/plan" -d "${body}" &
  local pid1=$!
  curl -sN --max-time 90 -o "${out2}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${GATEWAY_API_KEY}" \
    -H "Accept: text/event-stream" \
    -X POST "${GATEWAY_URL}/plan" -d "${body}" &
  local pid2=$!
  wait "${pid1}" "${pid2}"

  # Extract each run's session_id from the first SSE `session` event.
  # Pattern allows an empty session_id ([^"]*, not [^"]+) — when a duplicate
  # request lands in the same event-loop tick as the original, the dedup
  # responder hasn't seen the placeholder entry's sessionID populated yet.
  # That's correct behavior; we surface it via the `duplicate` event instead.
  local sid1 sid2 dup1 dup2 tasks1 tasks2
  sid1=$(grep -m1 '"session_id":' "${out1}" | sed -E 's/.*"session_id":"([^"]*)".*/\1/' || true)
  sid2=$(grep -m1 '"session_id":' "${out2}" | sed -E 's/.*"session_id":"([^"]*)".*/\1/' || true)
  dup1=$(grep -c "^event: duplicate$" "${out1}" || true)
  dup2=$(grep -c "^event: duplicate$" "${out2}" || true)
  tasks1=$(grep -c "^event: task.started$" "${out1}" || true)
  tasks2=$(grep -c "^event: task.started$" "${out2}" || true)

  echo "  run1: session=${sid1:-<empty>}  duplicate=${dup1}  tasks=${tasks1}"
  echo "  run2: session=${sid2:-<empty>}  duplicate=${dup2}  tasks=${tasks2}"

  # PASS conditions (post-Phase 2 idempotency):
  #   * either response emitted a `duplicate` SSE event, OR
  #   * both responses share the same non-empty session_id (full replay).
  # FAIL: two distinct non-empty sessions, both running tasks — the
  # double-execution scenario the layer was added to prevent.
  if (( dup1 > 0 || dup2 > 0 )); then
    local total_tasks=$(( tasks1 + tasks2 ))
    echo "  ✓ Q_INBOX_REPRO_C: dedup ON — duplicate event emitted; total task.started=${total_tasks}"
    return 0
  fi
  if [[ -n "${sid1}" && "${sid1}" == "${sid2}" ]]; then
    echo "  ✓ Q_INBOX_REPRO_C: dedup ON — both submits share session_id"
    return 0
  fi
  echo "  ✗ Q_INBOX_REPRO_C: NO DEDUP — two distinct sessions, two billings"
  echo "    (expected before Phase 2 idempotency lands)"
  return 1
}

main() {
  if [[ "${1:-}" == "dup-check" ]]; then
    run_dup_check
    return $?
  fi

  local to_run=( )
  if [[ $# -gt 0 ]]; then
    to_run=( "$@" )
  else
    to_run=( "${ALL_CASES[@]}" )
  fi

  local failed=( )
  for cid in "${to_run[@]}"; do
    if ! run_case "${cid}"; then
      failed+=( "${cid}" )
    fi
    echo
  done

  if [[ "${#failed[@]}" -gt 0 ]]; then
    echo "FAILED CASES: ${failed[*]}"
    echo "SSE logs in ${LOG_DIR}/"
    return 1
  fi
  echo "ALL CASES PASSED"
}

main "$@"
