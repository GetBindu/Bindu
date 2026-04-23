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
    # ✅ Skip external call in CI
    if os.getenv("CI") == "true":
        return {"status": "skipped", "note": "skipped in CI"}

    try:
        response = requests.get(
            FACILITATOR_URL,
            timeout=5,
            verify=not SKIP_TLS
        )

        if response.status_code == 200:
            return {"status": "success", "code": 200}

        if response.status_code == 401:
            return {
                "status": "reachable",
                "code": 401,
                "note": "Authentication required"
            }

        return {"status": "unexpected", "code": response.status_code}

    except requests.RequestException:
        logger.warning("Facilitator request failed (SSL or network issue)")
        return {
            "status": "error",
            "message": "facilitator request failed"
        }