
def classify_intent(query: str) -> str:
    query = query.lower()

    if any(word in query for word in ["tax", "gst", "finance", "money"]):
        return "finance"
    elif any(word in query for word in ["law", "legal", "court", "act"]):
        return "legal"
    else:
        return "tech"


def route_db(intent: str) -> str:
    return f"db/{intent}.txt"