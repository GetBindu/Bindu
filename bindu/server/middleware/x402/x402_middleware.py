# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""X402 Payment Middleware for Bindu.

This middleware implements the x402 payment protocol for HTTP requests,
following the official Coinbase x402 specification.

Based on: https://github.com/coinbase/x402/blob/main/python/x402/src/x402/fastapi/middleware.py
"""

from __future__ import annotations

import json
from web3 import Web3

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from x402.common import x402_VERSION, find_matching_payment_requirements
from x402.encoding import safe_base64_decode
from x402.facilitator import FacilitatorClient, FacilitatorConfig
from x402.types import PaymentPayload, PaymentRequirements, x402PaymentRequiredResponse

from bindu.utils.logging import get_logger
from bindu.extensions.x402 import X402AgentExtension
from bindu.settings import app_settings
from bindu.common.models import AgentManifest, VerifyResponse

logger = get_logger("bindu.server.middleware.x402")

PROTECTED_PATH = "/"
PROTECTED_METHOD = "POST"
WEB3_RPC_TIMEOUT_SECONDS = 10
SUPPORTED_X402_VERSION = 1
SUPPORTED_PAYMENT_SCHEME = "exact"


class X402Middleware(BaseHTTPMiddleware):
    """Middleware enforcing x402 payment validation for protected JSON-RPC methods."""

    def __init__(
        self,
        app,
        manifest: AgentManifest,
        facilitator_config: FacilitatorConfig,
        x402_ext: X402AgentExtension | None,
        payment_requirements: list[PaymentRequirements],
    ):
        """Initialize middleware with manifest, facilitator, and payment configuration."""
        super().__init__(app)
        self.manifest = manifest
        self.x402_ext = x402_ext
        self.facilitator = FacilitatorClient(config=facilitator_config)
        self._payment_requirements = payment_requirements
        self.protected_path = PROTECTED_PATH
        self._web3_connections: dict[str, Web3] = {}

    def _get_web3_connection(self, network: str) -> tuple[Web3 | None, str | None]:
        """Get or create Web3 connection for a given network."""
        if network in self._web3_connections:
            return self._web3_connections[network], None

        rpc_url = app_settings.x402.rpc_urls.get(network)
        if not rpc_url:
            return None, f"No RPC configured for {network}"

        try:
            w3 = Web3(
                Web3.HTTPProvider(
                    rpc_url, request_kwargs={"timeout": WEB3_RPC_TIMEOUT_SECONDS}
                )
            )
            self._web3_connections[network] = w3
            return w3, None
        except Exception as e:
            logger.error(f"Failed to connect to {network}: {e}")
            return None, str(e)

    async def dispatch(self, request: Request, call_next) -> Response:
        """Intercept requests and enforce payment for protected methods."""
        if (
            not self.x402_ext
            or request.url.path != self.protected_path
            or request.method != PROTECTED_METHOD
        ):
            return await call_next(request)

        # -------------------------------
        # ✅ FIX: FAIL-CLOSED JSON PARSING
        # -------------------------------
        try:
            body = await request.body()
        except Exception as e:
            logger.warning(f"Failed to read request body: {e}")
            return self._create_402_response("Invalid request body")

        try:
            request_data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Malformed JSON body: {e}")
            return self._create_402_response(
                "Invalid JSON body for x402 payment validation"
            )

        method = request_data.get("method")

        if not isinstance(method, str):
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid or missing JSON-RPC method"},
            )

        # Recreate request after consuming body
        from starlette.requests import Request as StarletteRequest

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = StarletteRequest(request.scope, receive)

        if method not in app_settings.x402.protected_methods:
            return await call_next(request)

        # -------------------------------
        # Payment logic
        # -------------------------------
        payment_header = request.headers.get("X-PAYMENT", "")

        if not payment_header:
            return self._create_402_response("X-PAYMENT header required")

        try:
            payment_dict = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload.model_validate(payment_dict)
        except Exception as e:
            logger.warning(f"Invalid X-PAYMENT header: {e}")
            return self._create_402_response("Invalid X-PAYMENT header")

        selected_payment_requirements = find_matching_payment_requirements(
            self._payment_requirements, payment_payload
        )

        if not selected_payment_requirements:
            return self._create_402_response("No matching payment requirements")

        try:
            is_valid, error_reason = await self._validate_payment_manually(
                payment_payload, selected_payment_requirements
            )
        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return self._create_402_response("Payment verification failed")

        if not is_valid:
            return self._create_402_response(f"Invalid payment: {error_reason}")

        request.state.payment_payload = payment_payload
        request.state.payment_requirements = selected_payment_requirements
        request.state.verify_response = VerifyResponse(
            is_valid=True, invalid_reason=None
        )

        return await call_next(request)

    async def _validate_payment_manually(
        self, payment_payload: PaymentPayload, payment_requirements: PaymentRequirements
    ) -> tuple[bool, str | None]:
        """Validate payment payload manually using on-chain checks."""
        try:
            if (
                payment_payload.x402_version != SUPPORTED_X402_VERSION
                or payment_payload.scheme != SUPPORTED_PAYMENT_SCHEME
            ):
                return False, "Unsupported payment scheme"

            auth = payment_payload.payload.authorization
            payment_value = int(auth.value)
            required_value = int(payment_requirements.max_amount_required)

            if payment_value < required_value:
                return False, "Insufficient payment amount"

            if payment_payload.network != payment_requirements.network:
                return False, "Network mismatch"

            w3, _ = self._get_web3_connection(payment_payload.network)
            if w3 is None:
                return False, "Network connection failed"

            return True, None

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False, str(e)

    def _create_402_response(self, error: str) -> JSONResponse:
        """Create standardized 402 Payment Required response."""
        response_data = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=self._payment_requirements,
            error=error,
        ).model_dump(by_alias=True)

        response_data["agent"] = {
            "name": self.manifest.name,
            "description": self.manifest.description or "",
            "agentCard": "/.well-known/agent.json",
        }

        if self.manifest.did_extension and self.manifest.did_extension.did:
            response_data["agent"]["did"] = self.manifest.did_extension.did

        return JSONResponse(
            content=response_data,
            status_code=402,
            headers={"Content-Type": "application/json"},
        )