import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SOURCES = {
    "finance": [
        {"path": os.path.join(BASE_DIR, "db", "finance.txt"), "type": "free"},
        {"path": os.path.join(BASE_DIR, "db", "finance_premium.txt"), "type": "premium"},
    ]
}


def select_source(intent: str, query: str):
    sources = SOURCES.get(intent, [])
    if not sources:
        return None

    tokens = set(re.findall(r"\w+", query.lower()))
    premium_keywords = {"latest", "premium", "advanced"}

    if tokens & premium_keywords:
        for s in sources:
            if s["type"] == "premium":
                return s

    for s in sources:
        if s["type"] == "free":
            return s

    return sources[0]