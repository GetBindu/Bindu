"""Bindu Edge Tunnel Client - Gradio-Style Ephemeral Tunnels

Connects to Bindu Edge Gateway and automatically establishes an ephemeral tunnel.

Usage:
  # Basic usage (by default connects to bindus.getbindu.com, forwards to localhost:3773):
  uv run python -m bindu.edge_client
  
  # Custom edge server and local port:
   uv run python -m bindu.edge_client --edge-url wss://your-edge-server.com --local-port 8080
  
  # With debug logging:
  uv run python -m bindu.edge_client --debug

Architecture:
- Gradio-style ephemeral tunneling
- Connection = tunnel (no database)
- In-memory slug resolution
- Instant cleanup on disconnect
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import gzip
import json
import logging
import sys
import time
from typing import Any, Dict

import httpx
import websockets

log = logging.getLogger("bindu.edge_client")


async def forward_request_to_local(local_port: int, req: Dict[str, Any], timeout: int = 60) -> Dict[str, Any]:
    """Forward HTTP request to local server and return response."""
    method = req.get("method", "GET")
    path = req.get("path", "/")
    headers = req.get("headers", {}) or {}
    body = req.get("body")
    req_id = req.get("request_id", "unknown")
    
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
        else:
            request_body_bytes = body

    url = f"http://127.0.0.1:{local_port}{path}"
    start_time = time.time()
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.request(method, url, headers=headers, content=request_body_bytes)
            elapsed = time.time() - start_time
            log.debug(f"[{req_id}] Local server responded: {resp.status_code} in {elapsed:.2f}s")
        except Exception as e:
            elapsed = time.time() - start_time
            log.exception(f"[{req_id}] Error forwarding to local server after {elapsed:.2f}s")
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
        log.debug(f"[{req_id}] Binary response ({len(resp.content)} bytes)")
    else:
        # Text content - use as string
        try:
            response_body = resp.text
            log.debug(f"[{req_id}] Text response ({len(response_body)} chars)")
        except Exception as e:
            # If text decoding fails, treat as binary
            log.warning(f"[{req_id}] Failed to decode as text, treating as binary: {e}")
            response_body = base64.b64encode(resp.content).decode("ascii")
            body_encoding = "base64"

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
        log.warning(f"[{req_id}] Very large response: {payload_size / (1024*1024):.1f}MB")
    
    if payload_size > 1024:  # Compress if > 1KB
        compressed = gzip.compress(payload_json.encode("utf-8"))
        compression_ratio = 100 * len(compressed) / payload_size
        if len(compressed) < payload_size * 0.9:  # Only use if saves >10%
            log.debug(f"[{req_id}] Compressed: {payload_size} → {len(compressed)} bytes ({compression_ratio:.1f}%)")
            return {
                "type": "response",
                "request_id": req.get("request_id"),
                "compressed": True,
                "data": base64.b64encode(compressed).decode("ascii"),
            }
    
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
    
    for text_type in text_types:
        if text_type in content_type:
            return False
    
    # Binary types
    binary_types = [
        "image/",
        "video/",
        "audio/",
        "application/pdf",
        "application/octet-stream",
        "application/zip",
        "application/gzip",
        "application/x-tar",
        "application/vnd.",
        "font/",
    ]
    
    for binary_type in binary_types:
        if binary_type in content_type:
            return True
    
    # Default to text
    return False


async def send_ping(ws, interval: int = 10):
    """Send periodic pings to keep connection alive."""
    while True:
        try:
            ping = json.dumps({"type": "ping"})
            await ws.send(ping)
            await asyncio.sleep(interval)
        except Exception:
            return


async def handle_request_async(ws, local_port: int, msg: Dict[str, Any]):
    """Handle request forwarding in background task to avoid blocking ping/pong."""
    req_id = msg.get("request_id", "unknown")
    method = msg.get("method", "GET")
    path = msg.get("path", "/")
    log.info(f"📨 [{req_id}] {method} {path}")
    
    # Forward with timeout handling
    try:
        resp_payload = await forward_request_to_local(local_port, msg)
    except asyncio.TimeoutError:
        log.error(f"⏱️  Timeout forwarding to local server (req_id={req_id})")
        resp_payload = {
            "type": "response",
            "request_id": req_id,
            "status": 504,
            "headers": {"content-type": "text/plain"},
            "body": "Gateway Timeout: Local agent took too long to respond",
            "body_encoding": "text",
        }
    except Exception as e:
        log.exception(f"❌ Error handling request (req_id={req_id})")
        resp_payload = {
            "type": "response",
            "request_id": req_id,
            "status": 500,
            "headers": {"content-type": "text/plain"},
            "body": f"Internal error: {str(e)}",
            "body_encoding": "text",
        }
    
    status = resp_payload.get("status", 200)
    log.info(f"📤 [{req_id}] Response: {status}")
    
    try:
        await ws.send(json.dumps(resp_payload))
    except Exception:
        log.exception(f"❌ Failed to send response (req_id={req_id})")


async def run_client(edge_url: str, local_port: int, reconnect: bool = True):
    """
    Connect to edge gateway and handle tunnel lifecycle.
    
    Gradio-style flow:
    1. Connect to /ws (no token needed)
    2. Receive auto-generated public URL
    3. Forward requests to local server
    4. Auto-cleanup on disconnect
    """
    backoff = 1
    
    while True:
        try:
            # Build WebSocket URL (edge_url/ws)
            if not edge_url.endswith('/ws'):
                ws_url = f"{edge_url.rstrip('/')}/ws"
            else:
                ws_url = edge_url
            
            log.info(f"Connecting to edge gateway: {ws_url}")
            
            async with websockets.connect(ws_url) as ws:
                log.info("✅ WebSocket connected - waiting for tunnel info...")
                
                # Start ping task for heartbeat
                ping_task = asyncio.create_task(send_ping(ws))
                # Track background request tasks
                request_tasks = set()

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        log.warning("Received non-JSON message: %s", raw)
                        continue

                    mtype = msg.get("type")
                    
                    if mtype == "connected":
                        # Tunnel established! Display public URL
                        public_url = msg.get("public_url")
                        slug = msg.get("slug")
                        tunnel_id = msg.get("tunnel_id")
                        
                        print("\n" + "=" * 70)
                        print("🎉 TUNNEL ESTABLISHED!")
                        print("=" * 70)
                        print(f"📡 Tunnel ID:  {tunnel_id}")
                        print(f"🔗 Slug:       {slug}")
                        print(f"🌐 Public URL: {public_url}")
                        print(f"🏠 Local Port: {local_port}")
                        print("=" * 70)
                        print("\n💡 Your local server is now accessible at the public URL!")
                        print("Press Ctrl+C to disconnect and cleanup the tunnel.\n")
                        
                        # Reset backoff on successful connection
                        backoff = 1
                    
                    elif mtype == "request":
                        # Handle request in background task to avoid blocking ping/pong
                        task = asyncio.create_task(handle_request_async(ws, local_port, msg))
                        request_tasks.add(task)
                        task.add_done_callback(request_tasks.discard)
                    
                    elif mtype == "ping":
                        # Reply with pong immediately (don't block)
                        try:
                            await ws.send(json.dumps({"type": "pong"}))
                        except Exception:
                            log.exception("Failed to send pong")
                    
                    else:
                        log.debug(f"Unknown message type: {mtype}")

                ping_task.cancel()
                # Cancel any pending request tasks
                for task in request_tasks:
                    task.cancel()
                
        except websockets.exceptions.ConnectionClosed as e:
            log.warning(f"Connection closed: {e}")
        except Exception:
            log.exception("Connection failed or lost")
        
        if not reconnect:
            break
        
        log.info(f"Reconnecting in {backoff} seconds...")
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


def _parse_args():
    """Parse command line arguments."""
    p = argparse.ArgumentParser(
        description="Bindu Edge Tunnel Client - Gradio-Style Ephemeral Tunnels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        """
    )
    p.add_argument(
        "--edge-url",
        default="wss://bindus.getbindu.com",
        help="Edge gateway WebSocket URL (default: wss://bindus.getbindu.com)"
    )
    p.add_argument(
        "--local-port",
        type=int,
        default=3773,
        help="Local server port to forward requests to (default: 3773)"
    )
    p.add_argument(
        "--no-reconnect",
        action="store_true",
        help="Do not auto-reconnect on disconnect"
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return p.parse_args()


def main():
    """Main entry point."""
    args = _parse_args()
    
    # Configure logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    print("\n🚀 Bindu Edge Tunnel Client (Gradio-Style)")
    print(f"📍 Edge URL: {args.edge_url}")
    print(f"🏠 Local Port: {args.local_port}\n")
    
    try:
        asyncio.run(run_client(
            edge_url=args.edge_url,
            local_port=args.local_port,
            reconnect=not args.no_reconnect
        ))
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted - tunnel closed\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
