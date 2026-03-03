"""
Analyst Agent — LangGraph LCEL chain for structured analysis.
Receives raw research findings from Scout Agent.
Extracts claims, scores confidence, returns structured JSON.
Deployed as an independent Bindu microservice.
"""

import json
import os

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from bindu.penguin.bindufy import bindufy
load_dotenv(override=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.1,  # Low — analysis needs consistency
)


# ── Prompt ────────────────────────────────────────────────────────────────────
analysis_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a precise analytical agent. Your job is to analyze research findings and extract structured insights.

Given raw research findings, you must:
1. Extract 3-7 key claims from the research
2. Score each claim's confidence (high/medium/low) based on how well-supported it is
3. Identify the main theme
4. Write a concise summary (2-3 sentences)

You MUST respond with valid JSON only. No preamble, no explanation, no markdown.

Response format:
{{
  "theme": "main topic in 5-10 words",
  "summary": "2-3 sentence concise summary",
  "claims": [
    {{
      "claim": "specific factual statement",
      "confidence": "high|medium|low",
      "reasoning": "one sentence explaining the confidence score"
    }}
  ],
  "total_claims": <number>,
  "analysis_quality": "high|medium|low"
}}"""
    ),
    (
        "human",
        "Analyze these research findings:\n\n{findings}"
    )
])

# ── Chain ─────────────────────────────────────────────────────────────────────
analysis_chain = analysis_prompt | llm | StrOutputParser()

# ── Helper ────────────────────────────────────────────────────────────────────
def parse_analysis(raw: str) -> dict:
    """Safely parse LLM JSON output with fallback."""
    try:
        # Strip markdown fences if present
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        return json.loads(clean.strip())
    except Exception as e:
        print(f"⚠️ JSON parse failed: {e}")
        return {
            "theme": "Analysis unavailable",
            "summary": raw[:300] if raw else "No output",
            "claims": [],
            "total_claims": 0,
            "analysis_quality": "low",
        }

# ── Handler ───────────────────────────────────────────────────────────────────
def handler(messages: list[dict[str, str]]) -> str:
    """
    Bindu-compatible handler.
    Receives Scout's findings via A2A, returns structured analysis as JSON string.
    """
    if not messages:
        return json.dumps({"error": "No input received."})

    findings = messages[-1].get("content", "")
    if not findings:
        return json.dumps({"error": "Empty findings."})

    print(f"\n🧠 Analyst Agent — analyzing {len(findings)} chars of findings")

    try:
        raw_output = analysis_chain.invoke({"findings": findings})
        analysis = parse_analysis(raw_output)

        print(f"✅ Analyst completed")
        print(f"   Theme    : {analysis.get('theme', 'N/A')}")
        print(f"   Claims   : {analysis.get('total_claims', 0)}")
        print(f"   Quality  : {analysis.get('analysis_quality', 'N/A')}")

        return json.dumps(analysis, indent=2)

    except Exception as e:
        print(f"❌ Analyst failed: {e}")
        return json.dumps({"error": str(e)})


# ── Bindu config ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    config = {
        "author": "nivasm2823@gmail.com",
        "name": "analyst-agent",
        "description": "LangGraph LCEL analysis agent. Extracts claims, scores confidence, returns structured JSON from research findings.",
        "capabilities": {"streaming": False},
        "deployment": {
            "url": "http://localhost:3782",
            "expose": True,
            "protocol_version": "1.0.0",
        },
        "storage": {"type": "memory"},
        "scheduler": {
            "type": "redis",
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        },
    }

    bindufy(config=config, handler=handler)