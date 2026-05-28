"""End-to-end driver: real Bindu agent + real fake facilitator + real HTTP.

Boots both servers as subprocesses, drives each #562 scenario with a real
POST to the agent's JSON-RPC endpoint, and prints the observed outcomes.

Run: ``uv run python tests/e2e/x402_scenarios/run_e2e.py``
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from x402 import PaymentPayload, PaymentRequirements

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]

AGENT_URL = "http://127.0.0.1:3773"
FACILITATOR_URL = "http://127.0.0.1:3775"

# Mirror the agent's published requirements (read from the 402 body once;
# the asset address is the canonical Base Sepolia USDC contract.)
PAY_TO = "0xa11ce0000000000000000000000000000000a11ce"
USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

REQUIREMENT = PaymentRequirements(
    scheme="exact",
    network="eip155:84532",
    asset=USDC_BASE_SEPOLIA,
    amount="10000",
    pay_to=PAY_TO,
    max_timeout_seconds=60,
    extra={"name": "USDC", "version": "2"},
)


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------


def spawn(
    label: str,
    args: list[str],
    env: dict[str, str] | None = None,
    log_path: Path | None = None,
):
    """Spawn a subprocess and (optionally) tee its stdio to a log file."""
    print(f"  ► launching {label}: {' '.join(args)}")
    full_env = {**os.environ, **(env or {})}
    stdout: Any = subprocess.DEVNULL
    stderr: Any = subprocess.DEVNULL
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path.open("wb")
        stdout = log_file
        stderr = subprocess.STDOUT
    return subprocess.Popen(
        args,
        cwd=str(REPO_ROOT),
        env=full_env,
        stdout=stdout,
        stderr=stderr,
    )


async def wait_for(url: str, timeout: float = 30.0, label: str = "") -> None:
    """Poll the URL until it answers below HTTP 500 or the timeout elapses."""
    deadline = time.time() + timeout
    async with httpx.AsyncClient(timeout=2.0) as client:
        while time.time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    print(f"  ✓ {label or url} ready (HTTP {resp.status_code})")
                    return
            except (httpx.RequestError, httpx.HTTPError):
                pass
            await asyncio.sleep(0.3)
    raise TimeoutError(f"{label or url} did not become ready within {timeout}s")


# ---------------------------------------------------------------------------
# Payment construction
# ---------------------------------------------------------------------------


def build_x_payment_header(
    nonce: str, payer: str = "0x000000000000000000000000000000000000beef"
) -> str:
    """Construct a base64-encoded EIP-3009 X-PAYMENT header for the canonical req."""
    payload = PaymentPayload(
        x402_version=2,
        payload={
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": payer,
                "to": PAY_TO,
                "value": "10000",
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": nonce,
            },
        },
        accepted=REQUIREMENT,
    )
    return base64.b64encode(payload.model_dump_json(by_alias=True).encode()).decode()


def message_send_body(
    task_id: uuid.UUID, context_id: uuid.UUID, text: str = "hi"
) -> dict[str, Any]:
    """Build a JSON-RPC ``message/send`` body for a task."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "message/send",
        "params": {
            "configuration": {"accepted_output_modes": ["text"]},
            "message": {
                "role": "user",
                "kind": "message",
                "parts": [{"kind": "text", "text": text}],
                "messageId": str(uuid.uuid4()),
                "contextId": str(context_id),
                "taskId": str(task_id),
            },
        },
    }


def task_get_body(task_id: uuid.UUID) -> dict[str, Any]:
    """Build a JSON-RPC ``tasks/get`` body for polling task state."""
    return {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tasks/get",
        "params": {"taskId": str(task_id)},
    }


# ---------------------------------------------------------------------------
# Scenario helpers
# ---------------------------------------------------------------------------


async def poll_task(
    client: httpx.AsyncClient, task_id: uuid.UUID, timeout: float = 8.0
) -> dict[str, Any]:
    """Poll tasks/get until terminal or timeout."""
    deadline = time.time() + timeout
    last_result: dict[str, Any] = {}
    while time.time() < deadline:
        resp = await client.post(AGENT_URL + "/", json=task_get_body(task_id))
        body = resp.json()
        result = body.get("result") or {}
        last_result = result
        state = (result.get("status") or {}).get("state")
        if state in ("completed", "failed", "rejected", "canceled"):
            return result
        await asyncio.sleep(0.2)
    return last_result


def heading(label: str) -> None:
    """Print a scenario banner to stdout."""
    print()
    print("=" * 78)
    print(label)
    print("=" * 78)


def summarize_task(label: str, result: dict[str, Any]) -> None:
    """Pretty-print task state, metadata, last agent message, and artifact preview."""
    state = (result.get("status") or {}).get("state", "(no result)")
    artifacts = result.get("artifacts") or []
    meta = result.get("metadata") or {}
    print(f"  {label}")
    print(f"    state:             {state}")
    print(f"    artifacts:         {len(artifacts)}")
    if meta:
        for k, v in meta.items():
            value_repr = (
                v if not isinstance(v, (dict, list)) else json.dumps(v)[:60] + "..."
            )
            print(f"    metadata.{k}: {value_repr}")
    else:
        print("    metadata:          (empty)")
    # Surface the last history message — for failed settles this carries
    # the "settlement failed; task not executed" explanation.
    history = result.get("history") or []
    for msg in reversed(history):
        if msg.get("role") == "agent":
            for part in msg.get("parts", []):
                if part.get("kind") == "text":
                    text = part.get("text", "")[:80]
                    print(f"    last agent msg:    {text}")
                    break
            break
    if artifacts:
        for part in artifacts[0].get("parts", []):
            if part.get("kind") == "text":
                print(f"    artifact preview:  {part.get('text', '')[:80]}")
                break


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


async def scenario_1_drain(client: httpx.AsyncClient) -> None:
    """Scenario 1: settle fails because the payer drained their wallet."""
    heading("Scenario 1 — Mallory drains wallet between verify and settle")
    print("  Nonce prefix 0xfa11 → mock_facilitator returns success=False on /settle.")
    task_id = uuid.uuid4()
    context_id = uuid.uuid4()
    headers = {"X-PAYMENT": build_x_payment_header(nonce="0xfa11" + "00" * 30)}
    resp = await client.post(
        AGENT_URL + "/", json=message_send_body(task_id, context_id), headers=headers
    )
    print(f"  message/send → HTTP {resp.status_code}")
    result = await poll_task(client, task_id)
    summarize_task("task result:", result)


async def scenario_2_timeout(client: httpx.AsyncClient) -> None:
    """Scenario 2: facilitator times out / 500s during /settle."""
    heading("Scenario 2 — facilitator hangs on /settle (client-side timeout)")
    print("  Nonce prefix 0xcdcd → mock_facilitator sleeps 10s then 500s.")
    print(
        "  Bindu's facilitator client raises a connect/read timeout long before that."
    )
    task_id = uuid.uuid4()
    context_id = uuid.uuid4()
    headers = {"X-PAYMENT": build_x_payment_header(nonce="0xcdcd" + "00" * 30)}
    resp = await client.post(
        AGENT_URL + "/", json=message_send_body(task_id, context_id), headers=headers
    )
    print(f"  message/send → HTTP {resp.status_code}")
    result = await poll_task(client, task_id, timeout=12.0)
    summarize_task("task result:", result)


async def scenario_3_parallel_double_spend(client: httpx.AsyncClient) -> None:
    """Scenario 3: two parallel requests; second nonce loses the settle race."""
    heading("Scenario 3 — two parallel requests, second nonce loses the settle race")
    print("  Nonce A normal (settles OK), nonce B = 0xfa11... (settle fails).")
    task_a = uuid.uuid4()
    task_b = uuid.uuid4()
    ctx_a = uuid.uuid4()
    ctx_b = uuid.uuid4()
    nonce_a = "0xa1" + uuid.uuid4().hex + uuid.uuid4().hex[:30]
    nonce_b = "0xfa11" + uuid.uuid4().hex + uuid.uuid4().hex[:28]
    hdr_a = {"X-PAYMENT": build_x_payment_header(nonce=nonce_a, payer="0x" + "b0" * 20)}
    hdr_b = {"X-PAYMENT": build_x_payment_header(nonce=nonce_b, payer="0x" + "b0" * 20)}

    # Fire both at once.
    resp_a_task, resp_b_task = await asyncio.gather(
        client.post(
            AGENT_URL + "/", json=message_send_body(task_a, ctx_a), headers=hdr_a
        ),
        client.post(
            AGENT_URL + "/", json=message_send_body(task_b, ctx_b), headers=hdr_b
        ),
    )
    print(f"  request A → HTTP {resp_a_task.status_code}")
    print(f"  request B → HTTP {resp_b_task.status_code}")

    result_a = await poll_task(client, task_a)
    result_b = await poll_task(client, task_b)
    summarize_task("task A (good settle):", result_a)
    summarize_task("task B (failed settle):", result_b)


async def scenario_4_replay(client: httpx.AsyncClient) -> None:
    """Scenario 4: identical X-PAYMENT replayed — middleware rejects the second."""
    heading("Scenario 4 — Mallory replays the same X-PAYMENT header")
    print("  Same nonce on both requests; nonce store catches the second one.")
    nonce = "0xee" + uuid.uuid4().hex + uuid.uuid4().hex[:30]
    headers = {"X-PAYMENT": build_x_payment_header(nonce=nonce)}

    task_id1 = uuid.uuid4()
    task_id2 = uuid.uuid4()
    ctx = uuid.uuid4()

    resp1 = await client.post(
        AGENT_URL + "/", json=message_send_body(task_id1, ctx), headers=headers
    )
    print(f"  first request  → HTTP {resp1.status_code}")
    resp2 = await client.post(
        AGENT_URL + "/", json=message_send_body(task_id2, ctx), headers=headers
    )
    print(f"  second request → HTTP {resp2.status_code}")
    body2 = resp2.json()
    print(
        f"  second request body.error → {body2.get('error') if isinstance(body2, dict) else body2}"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> int:
    """Boot facilitator + agent subprocesses, drive all four scenarios, tear down."""
    heading("Boot")
    log_dir = HERE / "logs"
    facilitator_proc = spawn(
        "mock facilitator",
        [
            sys.executable,
            "-m",
            "uvicorn",
            "tests.e2e.x402_scenarios.mock_facilitator:app",
            "--host",
            "127.0.0.1",
            "--port",
            "3775",
            "--log-level",
            "warning",
        ],
        log_path=log_dir / "facilitator.log",
    )
    # The agent reads X402__FACILITATOR_URL on import, and the docs path
    # uses ``python agent.py`` directly.
    agent_proc = spawn(
        "bindu agent",
        [sys.executable, "tests/e2e/x402_scenarios/agent.py"],
        env={"X402__FACILITATOR_URL": FACILITATOR_URL},
        log_path=log_dir / "agent.log",
    )

    try:
        await wait_for(
            FACILITATOR_URL + "/supported", timeout=15.0, label="facilitator"
        )
        await wait_for(AGENT_URL + "/health", timeout=45.0, label="agent")

        async with httpx.AsyncClient(timeout=15.0) as client:
            await scenario_1_drain(client)
            await scenario_2_timeout(client)
            await scenario_3_parallel_double_spend(client)
            await scenario_4_replay(client)

        heading("Done")
        print("  All four scenarios driven against real Bindu + real HTTP.")
        return 0
    finally:
        for proc, name in [(agent_proc, "agent"), (facilitator_proc, "facilitator")]:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
            except (subprocess.TimeoutExpired, ProcessLookupError):
                proc.kill()
        print("  ► subprocesses terminated")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
