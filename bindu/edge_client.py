"""Bindu Edge Tunnel Client

This small module connects to a Bindu Edge Gateway WebSocket tunnel and
forwards incoming HTTP requests to a local agent HTTP server (default
`localhost:3773`). It sends responses back via the tunnel.

Usage:
  # Using config file (recommended):
  python -m bindu.edge_client
  
  # Or with custom config file:
  python -m bindu.edge_client --config /path/to/config.json
  
  # Or with CLI arguments:
  python -m bindu.edge_client --ws-url ws://34.0.0.30:8080/ws/tunnel_test123 \
      --token test-token-123 --local-port 3773

Config file (edge.config.json in project root):
  {
    "ws_url": "ws://localhost:8001/ws/t_xxxxx",
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "local_port": 3773
  }

Notes:
- The user must register the tunnel on the control plane (associate
  the tunnel with the agent) separately; instructions are in the
  README change.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import gzip
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
import websockets

log = logging.getLogger("bindu.edge_client")


async def forward_request_to_local(local_port: int, req: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    method = req.get("method", "GET")
    path = req.get("path", "/")
    headers = req.get("headers", {}) or {}
    body = req.get("body")
    req_id = req.get("request_id", "unknown")
    
    log.info(f"[{req_id}] Forwarding {method} {path}")
    
    # Handle request body - support both string and base64-encoded binary
    request_body_bytes = None
    if body:
        if isinstance(body, str):
            # Check if it's base64 encoded (from a binary request)
            if req.get("body_encoding") == "base64":
                try:
                    request_body_bytes = base64.b64decode(body)
                    log.debug(f"[{req_id}] Decoded base64 request body: {len(request_body_bytes)} bytes")
                except Exception as e:
                    log.warning(f"[{req_id}] Failed to decode base64 body: {e}")
                    request_body_bytes = body.encode("utf-8")
            else:
                request_body_bytes = body.encode("utf-8")
                log.debug(f"[{req_id}] Request body: {len(request_body_bytes)} bytes")
        else:
            request_body_bytes = body

    url = f"http://127.0.0.1:{local_port}{path}"
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(method, url, headers=headers, content=request_body_bytes)
            elapsed = time.time() - start_time
            log.info(f"[{req_id}] Local server responded: {resp.status_code} in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            log.exception(f"[{req_id}] Error forwarding request to local server after {elapsed:.2f}s")
            return {
                "type": "response",
                "request_id": req.get("request_id"),
                "status": 502,
                "headers": {"content-type": "text/plain"},
                "body": f"Agent error: {str(e)}",
                "body_encoding": "text",
            }

    # Determine if response is binary or text based on content-type
    content_type = resp.headers.get("content-type", "").lower()
    is_binary = _is_binary_content_type(content_type)
    
    # Handle response body - encode binary as base64, text as string
    response_body = None
    body_encoding = "text"
    
    if is_binary:
        # Binary content - encode as base64
        response_body = base64.b64encode(resp.content).decode("ascii")
        body_encoding = "base64"
        log.info(f"[{req_id}] Binary response (content-type: {content_type}), encoding as base64 ({len(resp.content)} bytes -> {len(response_body)} chars)")
    else:
        # Text content - use as string
        try:
            response_body = resp.text
            log.debug(f"[{req_id}] Text response ({len(response_body)} chars)")
        except Exception as e:
            # If text decoding fails, treat as binary
            log.warning(f"[{req_id}] Failed to decode response as text, treating as binary: {e}")
            response_body = base64.b64encode(resp.content).decode("ascii")
            body_encoding = "base64"
    
    # Log response headers for debugging
    log.debug(f"[{req_id}] Response headers: {dict(resp.headers)}")

    # Build response payload
    response_payload = {
        "type": "response",
        "request_id": req.get("request_id"),
        "status": resp.status_code,
        "headers": dict(resp.headers),
        "body": response_body,
        "body_encoding": body_encoding,
    }
    
    # Apply compression for large payloads (>1KB)
    payload_json = json.dumps(response_payload)
    payload_size = len(payload_json.encode("utf-8"))
    
    # Warn about very large payloads
    max_recommended_size = 10 * 1024 * 1024  # 10MB
    if payload_size > max_recommended_size:
        log.warning(f"[{req_id}] Very large response payload: {payload_size / (1024*1024):.1f}MB - may cause issues")
    
    if payload_size > 1024:  # Compress if > 1KB
        compressed = gzip.compress(payload_json.encode("utf-8"))
        compression_ratio = 100 * len(compressed) / payload_size
        if len(compressed) < payload_size * 0.9:  # Only use if saves >10%
            log.info(f"[{req_id}] Compressed response: {payload_size} -> {len(compressed)} bytes ({compression_ratio:.1f}%)")
            return {
                "type": "response",
                "request_id": req.get("request_id"),
                "compressed": True,
                "data": base64.b64encode(compressed).decode("ascii"),
            }
        else:
            log.debug(f"[{req_id}] Compression not beneficial: {compression_ratio:.1f}%")
    
    log.debug(f"[{req_id}] Returning uncompressed payload: {payload_size} bytes")
    return response_payload


def _is_binary_content_type(content_type: str) -> bool:
    """Determine if a content-type represents binary data."""
    # Text-based content types
    text_types = [
        "text/",
        "application/json",
        "application/javascript",
        "application/xml",
        "application/x-www-form-urlencoded",
        "application/ld+json",
        "application/rdf+xml",
        "application/soap+xml",
    ]
    
    # Check if it's a known text type
    for text_type in text_types:
        if text_type in content_type:
            return False
    
    # Binary types (images, videos, documents, etc.)
    binary_types = [
        "image/",
        "video/",
        "audio/",
        "application/pdf",
        "application/octet-stream",
        "application/zip",
        "application/gzip",
        "application/x-tar",
        "application/vnd.",  # Various vendor-specific formats
        "font/",
    ]
    
    for binary_type in binary_types:
        if binary_type in content_type:
            return True
    
    # Default to text for unknown types
    return False


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
                        
                        # Forward with timeout handling
                        try:
                            resp_payload = await forward_request_to_local(local_port, msg)
                        except asyncio.TimeoutError:
                            log.error(f"Timeout forwarding request to local agent (req_id={req_id})")
                            resp_payload = {
                                "type": "response",
                                "request_id": req_id,
                                "status": 504,
                                "headers": {"content-type": "text/plain"},
                                "body": "Gateway Timeout: Local agent took too long to respond",
                                "body_encoding": "text",
                            }
                        
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


def _find_project_root() -> Optional[Path]:
    """Find the project root by looking for pyproject.toml or .git directory."""
    current = Path.cwd()
    
    # Check current directory and parents
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists() or (parent / ".git").exists():
            return parent
    
    return None


def _load_config_file(config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load configuration from JSON file.
    
    Priority order:
    1. Explicitly provided config_path via --config
    2. edge.config.json in project root
    
    Args:
        config_path: Path to config file. If None, searches project root.
    
    Returns:
        Dict with configuration or None if file not found
    """
    paths_to_try = []
    
    if config_path:
        # Explicit config path provided
        paths_to_try.append(Path(config_path))
    else:
        # Try project root only
        project_root = _find_project_root()
        if project_root:
            paths_to_try.append(project_root / "edge.config.json")
    
    for path in paths_to_try:
        if path.exists():
            try:
                with open(path, 'r') as f:
                    config = json.load(f)
                    log.info(f"Loaded configuration from {path}")
                    return config
            except Exception as e:
                log.error(f"Failed to load config file {path}: {e}")
                continue
    
    return None


def _parse_args():
    p = argparse.ArgumentParser(description="Bindu Edge Tunnel Client")
    p.add_argument("--config", help="Path to config file (default: edge.config.json in project root)")
    p.add_argument("--ws-url", help="WebSocket tunnel URL")
    p.add_argument("--token", help="Tunnel token (X-Tunnel-Token)")
    p.add_argument("--local-port", type=int, help="Local agent HTTP port (default: 3773)")
    p.add_argument("--no-reconnect", action="store_true", help="Do not reconnect on disconnect")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


def main():
    args = _parse_args()
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")
    
    # Load config from file
    config = _load_config_file(args.config)
    
    # Get values from CLI args or config file (CLI args take precedence)
    ws_url = args.ws_url or (config.get("ws_url") if config else None)
    token = args.token or (config.get("token") if config else None)
    local_port = args.local_port or (config.get("local_port") if config else 3773)
    
    # Validate required parameters
    if not ws_url:
        log.error("WebSocket URL not provided. Use --ws-url or create edge.config.json in project root.")
        return
    
    if not token:
        log.error("Token not provided. Use --token or create edge.config.json in project root.")
        return
    
    log.info(f"Starting edge client: ws_url={ws_url}, local_port={local_port}")
    
    try:
        asyncio.run(run_client(ws_url, token, local_port, reconnect=not args.no_reconnect))
    except KeyboardInterrupt:
        log.info("Interrupted, exiting")


if __name__ == "__main__":
    main()