"""X402 Payment Middleware for Bindu.

This middleware enforces payment validation using the x402 protocol.
Ensures fail-closed behavior to prevent malformed request bypass.
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

        rpc_map = getattr(app_settings.x402, "rpc_urls_by_network", None)
        timeout = getattr(app_settings.x402, "rpc_timeout", 10)

        if not isinstance(rpc_map, dict):
            return None, "RPC configuration missing"

        rpc_urls = rpc_map.get(network)

        if isinstance(rpc_urls, list) and rpc_urls:
            rpc_url = rpc_urls[0]
        else:
            rpc_url = rpc_urls

        if not isinstance(rpc_url, str):
            return None, f"No RPC configured for {network}"

        try:
            w3 = Web3(
                Web3.HTTPProvider(
                    rpc_url,
                    request_kwargs={"timeout": timeout},
                )
            )

            if not w3.is_connected():
                return None, "RPC connection failed"

            self._web3_connections[network] = w3
            return w3, None

        except Exception as e:
            logger.error(f"Web3 connection failed: {e}")
            return None, "RPC connection error"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Intercept requests and enforce payment."""
        if (
            not self.x402_ext
            or request.url.path != self.protected_path
            or request.method != PROTECTED_METHOD
        ):
            return await call_next(request)

        # -------- FAIL-CLOSED JSON --------
        try:
            body = await request.body()
            data = json.loads(body.decode("utf-8"))
        except Exception:
            return self._create_402_response("Invalid request body")

        if not isinstance(data, dict):
            return JSONResponse(status_code=400, content={"error": "Invalid payload"})

        method = data.get("method")
        if not isinstance(method, str):
            return JSONResponse(status_code=400, content={"error": "Invalid method"})

        from starlette.requests import Request as StarletteRequest

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = StarletteRequest(request.scope, receive)

        if method not in app_settings.x402.protected_methods:
            return await call_next(request)

        # -------- PAYMENT --------
        payment_header = request.headers.get("X-PAYMENT")
        if not payment_header:
            return self._create_402_response("Missing payment")

        try:
            decoded = json.loads(safe_base64_decode(payment_header))
            payment_payload = PaymentPayload.model_validate(decoded)
        except Exception:
            return self._create_402_response("Invalid payment header")

        selected = find_matching_payment_requirements(
            self._payment_requirements, payment_payload
        )
        if not selected:
            return self._create_402_response("No matching requirements")

        valid, reason = await self._validate_payment(payment_payload, selected)
        if not valid:
            return self._create_402_response(reason or "Invalid payment")

        request.state.verify_response = VerifyResponse(
            is_valid=True, invalid_reason=None
        )

        return await call_next(request)

    async def _validate_payment(
        self,
        payment_payload: PaymentPayload,
        payment_requirements: PaymentRequirements,
    ) -> tuple[bool, str | None]:
        """Validate payment payload using basic security checks."""
        try:
            if (
                payment_payload.x402_version != SUPPORTED_X402_VERSION
                or payment_payload.scheme != SUPPORTED_PAYMENT_SCHEME
            ):
                return False, "Invalid scheme"

            if payment_payload.network != payment_requirements.network:
                return False, "Network mismatch"

            auth = payment_payload.payload.authorization
            payment_value = int(auth.value)
            required_value = int(payment_requirements.max_amount_required)

            if payment_value < required_value:
                return False, "Insufficient payment amount"

            w3, _ = self._get_web3_connection(payment_payload.network)
            if w3 is None:
                return False, "Network unavailable"

            return True, None

        except Exception as e:
            logger.error(f"Validation error: {e}", exc_info=True)
            return False, "Validation failed"

    def _create_402_response(self, error: str) -> JSONResponse:
        """Create standardized 402 Payment Required response."""
        response = x402PaymentRequiredResponse(
            x402_version=x402_VERSION,
            accepts=self._payment_requirements,
            error=error,
        ).model_dump(by_alias=True)

        response["agent"] = {
            "name": self.manifest.name,
            "description": self.manifest.description or "",
            "agentCard": "/.well-known/agent.json",
        }

        if self.manifest.did_extension and self.manifest.did_extension.did:
            response["agent"]["did"] = self.manifest.did_extension.did

        return JSONResponse(content=response, status_code=402)
