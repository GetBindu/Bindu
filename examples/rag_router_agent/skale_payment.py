import requests
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
FACILITATOR_URL = os.getenv(
    "SKALE_FACILITATOR_URL",
    "https://facilitator.x402.fi"
)


def call_skale_facilitator():
    try:
        response = requests.get(FACILITATOR_URL, timeout=5, verify=False)  # ⚠️ disable SSL check

        if response.status_code == 200:
            return {
                "status": "success",
                "code": 200
            }

        elif response.status_code == 401:
            return {
                "status": "reachable",
                "code": 401,
                "note": "Authentication required (expected)"
            }

        else:
            return {
                "status": "unexpected_response",
                "code": response.status_code
            }

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }