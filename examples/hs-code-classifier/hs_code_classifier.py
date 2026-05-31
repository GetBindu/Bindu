"""
HS Code Classifier — Bindu Example

A trade compliance agent that classifies products into their correct
Harmonized System (HS) codes — the 6-digit international standard used
by customs authorities in every country to identify goods crossing borders.

Getting the HS code wrong means wrong tariffs, blocked shipments, or fines.
This agent helps SMBs get it right without hiring a trade lawyer.

Features
--------
- HS code classification backed by DuckDuckGo live web search
- Duty rates sourced from live search (not LLM memory)
- Compliance notes with misclassification risks
- Alternative codes with conditions

Prerequisites
-------------
    uv add bindu agno duckduckgo-search python-dotenv pydantic-settings

Usage
-----
    export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
    python hs_code_classifier.py

The agent will be live at http://localhost:3773
Example queries:
    "Classify cotton t-shirts for adults"
    "What HS code for lithium-ion batteries used in laptops?"
    "HS code for green coffee beans from Ethiopia"
"""

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from bindu.penguin.bindufy import bindufy
from bindu.utils.logging import get_logger
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Settings validation
# ---------------------------------------------------------------------------

class AppSettings(BaseSettings):
    """Application settings with validation."""

    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    bindu_deployment_url: str = Field(
        default="http://localhost:3773", alias="BINDU_DEPLOYMENT_URL"
    )

    class Config:
        env_file = ".env"

    def validate(self) -> None:
        """Validate required settings at startup."""
        if not self.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY is not set. "
                "Please set it in .env or as an environment variable."
            )


app_settings = AppSettings()


def validate_settings() -> None:
    """Startup-time validation of required settings."""
    try:
        app_settings.validate()
    except ValueError as e:
        logger.error("Configuration error: %s", e)
        raise


# ---------------------------------------------------------------------------
# 2. Agent definition
# ---------------------------------------------------------------------------

INSTRUCTIONS = """
You are an expert customs classification specialist with deep knowledge of the
Harmonized System (HS) — the international standard for classifying traded goods,
maintained by the World Customs Organization (WCO).

You have access to DuckDuckGo web search. You MUST use it to look up:
1. The correct HS code for the product (search WCO or official tariff databases)
2. Current duty rates for the trade routes requested (search official sources)
3. Any applicable trade agreements or compliance requirements

Never rely on memory alone for duty rates or tariff information — always search
and cite the source. If search results are unavailable, state this explicitly
and direct the user to official sources rather than providing unverified figures.

When asked to classify a product, respond in this exact structure:

HS CODE
Provide the 6-digit HS code (format: XXXX.XX) and the official WCO chapter heading.
Cite the source used to verify this code.

CLASSIFICATION RATIONALE
2-3 sentences explaining exactly why this code applies, referencing the relevant
HS chapter, heading, and subheading rules.

DUTY RATES
A table of indicative import duty rates for the most relevant trade routes:
- China → EU
- India → EU
- China → US
- India → US
Cite the source for each rate. Always include this disclaimer:

⚠️ These rates are indicative only, sourced from web search.
Verify before filing against official schedules:
- EU TARIC: https://ec.europa.eu/taxation_customs/dds2/taric/
- US HTS: https://hts.usitc.gov/

COMPLIANCE NOTES
2-3 bullet points covering:
- Common misclassification risks for this product type
- Any preferential trade agreements that may reduce duty (GSP, FTA)
- Required certifications or documentation for this HS code

ALTERNATIVE CODES
If there are common alternative codes that could apply depending on product
specifications, list them with a one-line explanation of when each applies.

Rules:
- Always use 6-digit HS codes (the international standard)
- If the product description is ambiguous, ask ONE clarifying question
- Never invent HS codes or duty rates — search first, then cite sources
- Output in plain Markdown
""".strip()

agent = Agent(
    instructions=INSTRUCTIONS,
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=app_settings.openrouter_api_key,  # pragma: allowlist secret
    ),
    tools=[DuckDuckGoTools()],
    markdown=True,
)


# ---------------------------------------------------------------------------
# 3. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "hs_code_classifier",
    "description": (
        "A trade compliance agent that classifies products into their correct "
        "Harmonized System (HS) codes using live web search, provides sourced "
        "duty rates for common trade routes, and flags compliance risks — "
        "helping SMBs avoid costly customs errors."
    ),
    "version": "1.0.0",
    "capabilities": {
        "classification": ["hs-code", "customs-classification", "trade-compliance"],
        "research": ["duty-rates", "trade-agreements", "compliance-notes"],
        "search": ["live-tariff-lookup", "duckduckgo"],
        "streaming": False,
    },
    "skills": ["skills/hs-classification-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": app_settings.bindu_deployment_url,
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
}


# ---------------------------------------------------------------------------
# 4. Handler
# ---------------------------------------------------------------------------

def handler(messages: list[dict[str, str]]):
    """Classify a product into its correct HS code using live web search.

    Args:
        messages: Standard A2A message list, e.g.
                  [{"role": "user", "content": "Classify cotton t-shirts for adults"}]

    Returns:
        HS code, classification rationale, duty rates (sourced from web search),
        compliance notes, and alternative codes.
    """
    try:
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return (
                "No product description received. "
                "Please describe the product you want to classify, e.g. "
                "'Classify cotton t-shirts for adults'."
            )

        query = user_messages[-1].get("content", "").strip()
        if not query:
            return (
                "Empty query. Please describe a product to classify, e.g. "
                "'What HS code for lithium-ion batteries used in laptops?'"
            )

        result = agent.run(input=messages)
        return result

    except Exception as e:
        logger.error("Classification error: %s", e, exc_info=True)
        return "Classification failed. Please try again or contact support."


# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    validate_settings()
    logger.info(
        "🛃 HS Code Classifier running at %s", app_settings.bindu_deployment_url
    )
    logger.info("📦 Example: Classify cotton t-shirts for adults")
    bindufy(config, handler)