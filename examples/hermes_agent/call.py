# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "cryptography>=42",
#   "base58>=2.1",
#   "httpx>=0.27",
# ]
# ///
"""Self-call the bindufied Hermes agent with DID-signed headers.

Reuses the agent's *own* Ed25519 key (`.bindu/private.pem`) as the caller
identity — simplest possible round-trip for local testing. For real calls
from a separate client, generate a fresh DID and point ``SEED_PEM`` at it.

Usage:
    uv run call.py "summarize bindu in one sentence"

What it does:
    1. Reads the agent's DID from /.well-known/agent.json.
    2. Signs the JSON-RPC body the way the server verifies — Ed25519 over
       ``json.dumps({"body": <raw>, "did": <did>, "timestamp": <ts>},
       sort_keys=True)``, then base58-encoded.
    3. POSTs ``message/send`` and polls ``tasks/get`` until a terminal state.
    4. Prints the artifact text.

Server invariant (don't fight it):
    The middleware hashes ``request.body.decode("utf-8")`` exactly as received.
    We compute the body string *once* with the same separators Python uses
    by default, then send those exact bytes — any re-serialization flips
    bytes and crypto verification returns ``reason="crypto_mismatch"``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

import base58
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).parent
SEED_PEM = HERE / ".bindu" / "private.pem"
OAUTH_CREDS = HERE / ".bindu" / "oauth_credentials.json"
BASE_URL = "http://localhost:3773"
HYDRA_TOKEN_URL = "https://hydra.getbindu.com/oauth2/token"

TERMINAL_STATES = {"completed", "failed", "canceled", "input-required", "auth-required", "payment-required"}


def get_bearer_token(client: httpx.Client) -> str:
    """Exchange client_credentials for a JWT against Hydra.

    The agent is registered with Hydra at boot; its credentials are written
    to ``.bindu/oauth_credentials.json``. Self-call reuses those — a real
    external client would have its own client_id/secret.
    """
    creds_map = json.loads(OAUTH_CREDS.read_text())
    # File is keyed by DID; there's exactly one entry for a single-agent process.
    creds = next(iter(creds_map.values()))
    r = client.post(
        HYDRA_TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "scope": " ".join(creds.get("scopes", ["agent:read", "agent:write"])),
        },
    )
    r.raise_for_status()
    return r.json()["access_token"]


def load_signer() -> Ed25519PrivateKey:
    pem = SEED_PEM.read_bytes()
    key = serialization.load_pem_private_key(pem, password=None)
    if not isinstance(key, Ed25519PrivateKey):
        sys.exit(f"{SEED_PEM} is not an Ed25519 key")
    return key


def fetch_agent_did(client: httpx.Client) -> str:
    card = client.get(f"{BASE_URL}/.well-known/agent.json").raise_for_status().json()
    for ext in card.get("capabilities", {}).get("extensions", []):
        uri = ext.get("uri", "")
        if uri.startswith("did:bindu:"):
            return uri
    sys.exit("agent card has no did:bindu: extension — is DID middleware enabled?")


def sign_request(signer: Ed25519PrivateKey, did: str, body: str) -> dict[str, str]:
    """Build the three X-DID-* headers the server's verifier reconstructs."""
    timestamp = int(time.time())
    # Match server: json.dumps(payload, sort_keys=True) — default separators
    # have a space after ":" and ",". Python's default does exactly that.
    payload = json.dumps({"body": body, "did": did, "timestamp": timestamp}, sort_keys=True)
    signature = signer.sign(payload.encode("utf-8"))
    return {
        "X-DID": did,
        "X-DID-Timestamp": str(timestamp),
        "X-DID-Signature": base58.b58encode(signature).decode("ascii"),
    }


def build_body(prompt: str) -> tuple[str, str]:
    """Return (body_json_string, task_id). Serialize once, send those exact bytes."""
    task_id = str(uuid.uuid4())
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": str(uuid.uuid4()),
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": prompt}],
                "kind": "message",
                "messageId": str(uuid.uuid4()),
                "contextId": str(uuid.uuid4()),
                "taskId": task_id,
            },
            "configuration": {"acceptedOutputModes": ["application/json"]},
        },
    }
    # Match server's default Python JSON spacing so the body we sign is
    # byte-identical to the body we send.
    return json.dumps(payload), task_id


def poll(client: httpx.Client, signer: Ed25519PrivateKey, did: str, bearer: str, task_id: str, timeout_s: float = 60.0) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        body, _ = build_get_body(task_id)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer}",
            **sign_request(signer, did, body),
        }
        r = client.post(BASE_URL + "/", content=body, headers=headers).raise_for_status().json()
        result = r.get("result", {})
        state = result.get("status", {}).get("state")
        if state in TERMINAL_STATES:
            return result
        time.sleep(1.0)
    sys.exit(f"timed out after {timeout_s}s waiting for task {task_id}")


def build_get_body(task_id: str) -> tuple[str, str]:
    payload = {
        "jsonrpc": "2.0",
        "method": "tasks/get",
        "id": str(uuid.uuid4()),
        "params": {"taskId": task_id},
    }
    return json.dumps(payload), task_id


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompt", nargs="?", default="summarize bindu in one sentence")
    ap.add_argument("--timeout", type=float, default=60.0, help="poll timeout in seconds (default: 60)")
    args = ap.parse_args()

    signer = load_signer()
    with httpx.Client(timeout=30.0) as client:
        did = fetch_agent_did(client)
        print(f"[call] agent DID: {did}")

        bearer = get_bearer_token(client)
        print(f"[call] got Hydra JWT ({len(bearer)} chars)")

        body, task_id = build_body(args.prompt)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {bearer}",
            **sign_request(signer, did, body),
        }
        submit = client.post(BASE_URL + "/", content=body, headers=headers).raise_for_status().json()
        state = submit.get("result", {}).get("status", {}).get("state")
        print(f"[call] submitted task {task_id} → state={state}")

        result = poll(client, signer, did, bearer, task_id, timeout_s=args.timeout)
        final_state = result.get("status", {}).get("state")
        print(f"[call] final state: {final_state}\n")

        artifacts = result.get("artifacts") or []
        if not artifacts:
            print("(no artifacts)")
            print(json.dumps(result, indent=2))
            return
        for a in artifacts:
            for p in a.get("parts", []):
                if p.get("kind") == "text":
                    print(p.get("text", ""))


if __name__ == "__main__":
    main()
