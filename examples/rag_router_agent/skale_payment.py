import requests

# 🔗 Choose one facilitator (can be swapped easily)
FACILITATOR_URL = "https://facilitator.x402.fi"


def call_skale_facilitator() -> dict:
    """
    Minimal prototype for SKALE facilitator integration.

    This simulates an x402 payment call by checking connectivity
    with a facilitator endpoint.

    NOTE:
    - No authentication is included (expected 401 response).
    - This is intentional for prototype validation.
    """

    try:
        # 🔐 Minimal headers (good practice even for prototype)
        headers = {
            "Content-Type": "application/json"
        }

        response = requests.get(
            FACILITATOR_URL,
            headers=headers,
            timeout=5
        )

        status_code = response.status_code

        # ✅ Successful response
        if status_code == 200:
            return {
                "status": "success",
                "message": "Facilitator reachable",
                "code": status_code
            }

        # ⚠️ Expected case (no auth yet)
        elif status_code == 401:
            return {
                "status": "reachable",
                "code": status_code,
                "note": "Authentication required (expected for prototype)"
            }

        # ⚠️ Other responses
        else:
            return {
                "status": "unexpected_response",
                "code": status_code,
                "response_preview": response.text[:200]
            }

    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "message": "Request timed out"
        }

    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": "Connection failed"
        }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }