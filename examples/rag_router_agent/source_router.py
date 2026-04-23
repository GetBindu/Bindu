import os

# 📁 Resolve base directory safely (important fix)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 🔀 Source routing with cost awareness
SOURCES = {
    "finance": [
        {
            "path": os.path.join(BASE_DIR, "db", "finance.txt"),
            "type": "free"
        },
        {
            "path": os.path.join(BASE_DIR, "db", "finance_premium.txt"),
            "type": "premium",
            "cost": 0.01
        },
    ],
    "tech": [
        {
            "path": os.path.join(BASE_DIR, "db", "tech.txt"),
            "type": "free"
        },
    ],
    "legal": [
        {
            "path": os.path.join(BASE_DIR, "db", "legal.txt"),
            "type": "free"
        },
    ],
}


def select_source(intent: str, query: str):
    sources = SOURCES.get(intent, [])

    if not sources:
        return None

    query_lower = query.lower()

    # 🔥 Premium trigger heuristic
    premium_keywords = ["latest", "premium", "advanced", "pro"]

    # Try premium first if keywords match
    if any(word in query_lower for word in premium_keywords):
        for source in sources:
            if source.get("type") == "premium":
                return source

    # Fallback to free source
    for source in sources:
        if source.get("type") == "free":
            return source

    # Final fallback (edge case)
    return sources[0] if sources else None