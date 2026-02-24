"""Bindu x402 extension helpers.

Provides HTTP activation header utilities per A2A extensions mechanism.
"""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

from bindu.settings import app_settings


def is_activation_requested(request: Request) -> bool:
    """Check if the client requested x402 extension activation via header."""
    exts = request.headers.get("X-A2A-Extensions", "")
    return app_settings.x402.extension_uri in exts


def add_activation_header(response: Response) -> Response:
    """Echo the x402 extension URI in response header to confirm activation."""
    response.headers["X-A2A-Extensions"] = app_settings.x402.extension_uri
    return response
