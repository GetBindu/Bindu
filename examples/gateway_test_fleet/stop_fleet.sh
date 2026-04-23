#!/usr/bin/env bash
# Stop every agent started by start_fleet.sh.
#
# Reads pid files from pids/*.pid and sends SIGTERM. If an agent
# doesn't exit within 5s, SIGKILL. Removes the pid file on success.

set -euo pipefail

FLEET_DIR="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="${FLEET_DIR}/pids"

if [[ ! -d "${PID_DIR}" ]]; then
  echo "No pids directory — nothing to stop."
  exit 0
fi

shopt -s nullglob
pidfiles=( "${PID_DIR}"/*.pid )
shopt -u nullglob

if [[ "${#pidfiles[@]}" -eq 0 ]]; then
  echo "No pid files — nothing to stop."
  exit 0
fi

for pidfile in "${pidfiles[@]}"; do
  name="$(basename "${pidfile}" .pid)"
  pid="$(cat "${pidfile}" 2>/dev/null || true)"
  if [[ -z "${pid}" ]]; then
    rm -f "${pidfile}"
    continue
  fi
  if ! ps -p "${pid}" >/dev/null 2>&1; then
    echo "  [${name}] pid ${pid} not running"
    rm -f "${pidfile}"
    continue
  fi
  echo "  [${name}] stopping pid ${pid}..."
  kill -TERM "${pid}" 2>/dev/null || true

  # Wait up to 5 seconds for a clean exit.
  for _ in 1 2 3 4 5; do
    sleep 1
    ps -p "${pid}" >/dev/null 2>&1 || break
  done
  if ps -p "${pid}" >/dev/null 2>&1; then
    echo "  [${name}] didn't exit on SIGTERM — sending SIGKILL"
    kill -KILL "${pid}" 2>/dev/null || true
  fi
  rm -f "${pidfile}"
  echo "  [${name}] stopped"
done

echo "Fleet stopped."
