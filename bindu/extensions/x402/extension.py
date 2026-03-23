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


class X402ActivationHandler:
    """Handler for x402 extension activation in endpoints.

    Provides a unified interface for checking activation requests and
    adding activation headers to responses, reducing code duplication.
    """

    @staticmethod
    def is_requested(request: Request) -> bool:
        """Check if x402 activation is requested.

        Alias for is_activation_requested for cleaner endpoint code.
        """
        return is_activation_requested(request)

    @staticmethod
    def add_header(response: Response) -> Response:
        """Add x402 activation header to response.

        Alias for add_activation_header for cleaner endpoint code.
        """
        return add_activation_header(response)

    @staticmethod
    def check_and_activate(request: Request, response: Response) -> Response:
        """Check request and conditionally add activation header.

        Convenience method that combines checking and header addition.

        Args:
            request: Incoming HTTP request
            response: HTTP response to potentially modify

        Returns:
            Response with activation header if requested, unchanged otherwise
        """
        if is_activation_requested(request):
            return add_activation_header(response)
        return response
