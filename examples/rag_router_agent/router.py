import os
import re

# 🔤 Intent classification (robust token-based)
def classify_intent(query: str) -> str:
    words = re.findall(r"\w+", query.lower())

    if any(word in words for word in ["tax", "gst", "finance", "money"]):
        return "finance"
    elif any(word in words for word in ["law", "legal", "court"]):
        return "legal"
    else:
        return "tech"


# 📁 Resolve base directory safely
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# 📦 Route to correct DB
def route_db(intent: str) -> str:
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
    else:
        return tech_agent