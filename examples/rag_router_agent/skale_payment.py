import os
import requests
import logging

logger = logging.getLogger(__name__)

FACILITATOR_URL = os.getenv(
    "SKALE_FACILITATOR_URL",
    "https://facilitator.x402.fi"
)

SKIP_TLS = os.getenv("FACILITATOR_SKIP_TLS_VERIFY", "false").lower() == "true"


def call_skale_facilitator():
    """
    Calls the SKALE facilitator endpoint.

    Design:
    - Never block the agent flow
    - Always return one of: success, reachable, skipped
    - Treat ALL failures (HTTP + exceptions) as non-blocking
    """

    # ✅ Skip external calls in CI
    if os.getenv("CI") == "true":
        return {
            "status": "skipped",
            "note": "skipped in CI"
        }

    try:
        response = requests.get(
            FACILITATOR_URL,
            timeout=5,
            verify=not SKIP_TLS
        )

        # ✅ Success
        if response.ok:
            return {
                "status": "success",
                "code": response.status_code
            }

        # ✅ Auth required → still reachable
        if response.status_code == 401:
            return {
                "status": "reachable",
                "code": 401,
                "note": "authentication required"
            }

        # ✅ Transient errors (rate limit, server issues)
        if response.status_code == 429 or response.status_code >= 500:
            return {
                "status": "reachable",
                "code": response.status_code,
                "note": "transient facilitator error; proceeding with fallback"
            }

        # ✅ All other non-success responses → STILL non-blocking
        return {
            "status": "reachable",
            "code": response.status_code,
            "note": "non-success response; proceeding with fallback"
        }

    except requests.RequestException:
        # ✅ Network / SSL failure → non-blocking fallback
        logger.warning("Facilitator unreachable, falling back to non-blocking mode")

        return {
            "status": "reachable",
            "note": "facilitator unreachable (exception fallback)"
        }
        