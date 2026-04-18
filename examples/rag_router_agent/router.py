import os
import re


def classify_intent(query: str) -> str:
    # 🔤 Normalize + tokenize (fix substring + punctuation issues)
    words = re.findall(r"\w+", query.lower())

    if any(word in words for word in ["tax", "gst", "finance", "money"]):
        return "finance"
    elif any(word in words for word in ["law", "legal", "court"]):
        return "legal"
    else:
        return "tech"


# 📁 Resolve path relative to this file (fix cwd issue)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def route_db(intent: str) -> str:
    return os.path.join(BASE_DIR, "db", f"{intent}.txt")
