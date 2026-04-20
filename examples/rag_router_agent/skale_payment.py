import os
import requests

FACILITATOR_URL = os.getenv(
    "SKALE_FACILITATOR_URL",
    "https://facilitator.x402.fi"
)


def call_skale_facilitator() -> dict:
    """
    Prototype: checks facilitator reachability (NOT full x402 payment flow).

    This intentionally uses a simple GET request to verify connectivity only.
    """

    try:
        response = requests.get(FACILITATOR_URL, timeout=5)
        status_code = response.status_code

        if status_code == 200:
            return {
                "status": "success",
                "message": "Facilitator reachable",
                "code": status_code
            }

        elif status_code == 401:
            return {
                "status": "reachable",
                "code": status_code,
                "note": "Authentication required (expected for prototype)"
            }

        else:
            return {
                "status": "unexpected_response",
                "code": status_code
            }

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e)
        }