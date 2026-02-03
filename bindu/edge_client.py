"""Bindu Edge Tunnel Client

This small module connects to a Bindu Edge Gateway WebSocket tunnel and
forwards incoming HTTP requests to a local agent HTTP server (default
`localhost:3773`). It sends responses back via the tunnel.

Usage:
  python -m bindu.edge_client --ws-url ws://34.0.0.30:8080/ws/tunnel_test123 \
      --token test-token-123 --local-port 3773

Notes:
- The user must register the tunnel on the control plane (associate
  `tunnel_test123` with the agent) separately; instructions are in the
  README change.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import time
from typing import Any, Dict

import httpx
import websockets

log = logging.getLogger("bindu.edge_client")


async def forward_request_to_local(local_port: int, req: Dict[str, Any], timeout: int = 30) -> Dict[str, Any]:
    method = req.get("method", "GET")
    path = req.get("path", "/")
    headers = req.get("headers", {}) or {}
    body = req.get("body")
    data = body.encode() if body else None

    url = f"http://127.0.0.1:{local_port}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(method, url, headers=headers, content=data)
        except Exception as e:
            log.exception("Error forwarding request to local server")
            return {
                "type": "response",
                "request_id": req.get("request_id"),
                "status": 502,
                "headers": {"content-type": "text/plain"},
                "body": f"Agent error: {str(e)}",
            }

    return {
        "type": "response",
        "request_id": req.get("request_id"),
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": resp.text,
    }


async def send_ping(ws, interval: int = 10):
    while True:
        try:
            ping = json.dumps({"type": "ping", "ts": int(time.time())})
            await ws.send(ping)
        except Exception:
            return
        await asyncio.sleep(interval)


async def run_client(ws_url: str, token: str, local_port: int, reconnect: bool = True):
    backoff = 1
    while True:
        try:
            headers = [("X-Tunnel-Token", token)] if token else None
            log.info("Connecting to %s", ws_url)
            async with websockets.connect(ws_url, extra_headers=headers) as ws:
                log.info("Connected to edge tunnel")
                # start ping task
                ping_task = asyncio.create_task(send_ping(ws))

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        log.warning("Received non-json message: %s", raw)
                        continue

                    mtype = msg.get("type")
                    if mtype == "request":
                        # forward to local agent
                        req_id = msg.get("request_id", "unknown")
                        log.info("Received request: %s %s (req_id=%s)", msg.get("method"), msg.get("path"), req_id)
                        resp_payload = await forward_request_to_local(local_port, msg)
                        log.info("Sending response: status=%s (req_id=%s)", resp_payload.get("status"), req_id)
                        try:
                            await ws.send(json.dumps(resp_payload))
                            log.info("Response sent successfully (req_id=%s)", req_id)
                        except Exception:
                            log.exception("Failed to send response back to tunnel")
                    elif mtype == "ping":
                        # reply pong
                        await ws.send(json.dumps({"type": "pong", "ts": int(time.time())}))
                    elif mtype == "shutdown":
                        log.info("Received shutdown request from edge gateway")
                        ping_task.cancel()
                        return
                    else:
                        log.debug("Unhandled message type: %s", mtype)

                ping_task.cancel()
        except Exception:
            log.exception("Connection failed or lost")
        if not reconnect:
            break
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


def _parse_args():
    p = argparse.ArgumentParser(description="Bindu Edge Tunnel Client")
    p.add_argument("--ws-url", required=True, help="WebSocket tunnel URL")
    p.add_argument("--token", required=True, help="Tunnel token (X-Tunnel-Token)")
    p.add_argument("--local-port", type=int, default=3773, help="Local agent HTTP port")
    p.add_argument("--no-reconnect", action="store_true", help="Do not reconnect on disconnect")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = _parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    try:
        asyncio.run(run_client(args.ws_url, args.token, args.local_port, reconnect=not args.no_reconnect))
    except KeyboardInterrupt:
        log.info("Interrupted, exiting")


if __name__ == "__main__":
    main()