import os
import re
import sys

# 📁 Resolve base directory safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# (Optional but safer import handling)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# 🔤 Intent classification (robust + explicit)
def classify_intent(query: str) -> str | None:
    words = re.findall(r"\w+", query.lower())

    if any(w in words for w in ["tax", "gst", "finance", "money"]):
        return "finance"
    elif any(w in words for w in ["law", "legal", "court"]):
        return "legal"
    elif any(w in words for w in ["code", "api", "server", "computer", "tech"]):
        return "tech"
    else:
        return None  # ✅ important: handle unknown intent


# 📦 Route to correct DB
def route_db(intent: str) -> str | None:
    if intent is None:
        return None
    return os.path.join(BASE_DIR, "db", f"{intent}.txt")


# 🤖 Import domain agents (A2A delegation)
from agents.finance_agent import finance_agent
from agents.legal_agent import legal_agent
from agents.tech_agent import tech_agent


# 🔀 Route to correct agent
def route_agent(intent: str):
    if intent == "finance":
        return finance_agent
    elif intent == "legal":
        return legal_agent
    elif intent == "tech":
        return tech_agent
    else:
        return None  # ✅ important fallback