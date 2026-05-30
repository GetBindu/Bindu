"""
HS Code Classifier — Bindu Example

A trade compliance agent that classifies products into their correct
Harmonized System (HS) codes — the 6-digit international standard used
by customs authorities in every country to identify goods crossing borders.

Getting the HS code wrong means wrong tariffs, blocked shipments, or fines.
This agent helps SMBs get it right without hiring a trade lawyer.

Prerequisites
-------------
    uv add bindu agno python-dotenv pydantic-settings

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

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from bindu.utils.logging import get_logger
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# 1. Settings validation
# ---------------------------------------------------------------------------

class AppSettings(BaseSettings):
    """Application settings with validation."""

    openrouter_api_key: str = os.getenv("OPENROUTER_API_KEY", "")
    bindu_deployment_url: str = os.getenv(
        "BINDU_DEPLOYMENT_URL", "http://localhost:3773"
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
        logger.error(f"Configuration error: {e}")
        raise


# ---------------------------------------------------------------------------
# 2. Agent definition
# ---------------------------------------------------------------------------

INSTRUCTIONS = """
You are an expert customs classification specialist with deep knowledge of the
Harmonized System (HS) — the international standard for classifying traded goods,
maintained by the World Customs Organization (WCO).

When asked to classify a product, respond in this exact structure:

HS CODE
Provide the 6-digit HS code (format: XXXX.XX) and the official WCO chapter heading.

CLASSIFICATION RATIONALE
2-3 sentences explaining exactly why this code applies, referencing the relevant
HS chapter, heading, and subheading rules.

DUTY RATES
A table of indicative import duty rates for the most relevant trade routes:
- China → EU
- India → EU
- China → US
- India → US
Note: Always clarify these are indicative MFN rates and actual rates depend on
origin certificates, trade agreements, and current tariff schedules.

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
- Never invent HS codes — if genuinely uncertain, say so and suggest consulting
  a licensed customs broker
- Output in plain Markdown
""".strip()

agent = Agent(
    instructions=INSTRUCTIONS,
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=app_settings.openrouter_api_key,  # pragma: allowlist secret
    ),
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
        "Harmonized System (HS) codes, provides duty rates for common trade routes, "
        "and flags compliance risks — helping SMBs avoid costly customs errors."
    ),
    "version": "1.0.0",
    "capabilities": {
        "classification": ["hs-code", "customs-classification", "trade-compliance"],
        "research": ["duty-rates", "trade-agreements", "compliance-notes"],
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
    """Classify a product into its correct HS code.

    Args:
        messages: Standard A2A message list, e.g.
                  [{"role": "user", "content": "Classify cotton t-shirts for adults"}]

    Returns:
        HS code, classification rationale, duty rates, compliance notes,
        and alternative codes.
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
        logger.error(f"Classification error: {e}", exc_info=True)
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
