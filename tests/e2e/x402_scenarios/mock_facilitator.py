"""Programmable fake x402 facilitator for E2E scenario demos.

Implements the three endpoints Bindu actually calls — ``/supported``,
``/verify``, ``/settle`` — with deterministic failure modes keyed on the
EIP-3009 nonce prefix so the driver can demonstrate each #562 scenario
without doing any real on-chain work:

    nonce starts with ``0xfa11``  → /settle returns success=False (drain)
    nonce starts with ``0xcdcd``  → /settle sleeps then returns HTTP 500 (timeout)
    anything else                 → /settle returns success=True

Never use in production. The ``/verify`` endpoint always says yes.

Run: ``uv run python tests/e2e/x402_scenarios/mock_facilitator.py``
"""

from __future__ import annotations

import asyncio

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


async def supported(request: Request) -> JSONResponse:  # noqa: ARG001
    """Advertise Base Sepolia as a supported chain."""
    return JSONResponse(
        {
            "kinds": [
                {"x402Version": 2, "scheme": "exact", "network": "eip155:84532"},
            ],
            "extensions": [],
            "signers": {"eip155:*": ["0xf00df00df00df00df00df00df00df00df00df00d"]},
        }
    )


async def verify(request: Request) -> JSONResponse:
    """Accept every payment as valid; the worker pipeline is what we're exercising."""
    body = await request.json()
    payer = body["paymentPayload"]["payload"]["authorization"]["from"]
    return JSONResponse({"isValid": True, "invalidReason": None, "payer": payer})


async def settle(request: Request) -> JSONResponse:
    """Branch the settle response on nonce prefix to demonstrate each scenario."""
    body = await request.json()
    auth = body["paymentPayload"]["payload"]["authorization"]
    nonce = (auth.get("nonce") or "").lower()
    payer = auth["from"]
    network = body["paymentRequirements"]["network"]

    # Discriminator: special nonce prefixes opt into specific failure modes.
    if nonce.startswith("0xfa11"):
        # NB: x402 SDK's SettleResponse requires `transaction` to be a string
        # even on failure — null/None fails pydantic validation.
        return JSONResponse(
            {
                "success": False,
                "errorReason": "transfer reverted: insufficient balance",
                "payer": payer,
                "transaction": "",
                "network": network,
            }
        )
    if nonce.startswith("0xcdcd"):
        # Simulate a slow facilitator that ultimately fails. The client
        # configures its own httpx timeout shorter than this sleep, so it
        # observes a timeout exception.
        await asyncio.sleep(10.0)
        return JSONResponse({"error": "internal server error"}, status_code=500)

    # Happy path
    return JSONResponse(
        {
            "success": True,
            "errorReason": None,
            "payer": payer,
            "transaction": "0x" + "ab" * 32,
            "network": network,
        }
    )


app = Starlette(
    routes=[
        Route("/supported", supported, methods=["GET"]),
        Route("/verify", verify, methods=["POST"]),
        Route("/settle", settle, methods=["POST"]),
    ]
)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=3775, log_level="warning")
