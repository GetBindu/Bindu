"""
CBAM Carbon Calculator — Bindu Example

A trade compliance agent that helps EU importers understand their Carbon
Border Adjustment Mechanism (CBAM) obligations under EU Regulation 2023/956.

CBAM entered its definitive phase on 1 January 2026. Importers of covered
goods (iron & steel, aluminium, cement, fertilizers, hydrogen, electricity)
must now purchase and surrender CBAM certificates proportional to the
embedded carbon emissions in their imports.

Getting this wrong means blocked shipments, fines, or unexpected carbon costs
that wipe out margins. This agent helps SMBs understand their exposure before
they file.

Prerequisites
-------------
    uv add bindu agno python-dotenv

Usage
-----
    export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
    python cbam_calculator.py

The agent will be live at http://localhost:3773
Example queries:
    "Do I need CBAM for importing steel pipes from China?"
    "Calculate CBAM cost for 200 tonnes of aluminium from Turkey"
    "Am I exempt from CBAM if I import 30 tonnes of cement per year?"
"""

import os

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# 1. Agent definition
# ---------------------------------------------------------------------------

INSTRUCTIONS = """
You are an expert EU trade compliance specialist with deep knowledge of the
Carbon Border Adjustment Mechanism (CBAM) — EU Regulation 2023/956, which
entered its definitive phase on 1 January 2026.

When asked about CBAM, respond in this exact structure:

CBAM APPLICABILITY
State clearly whether CBAM applies to the described goods.
Reference the specific sector and CN (Combined Nomenclature) code if known.

EXEMPTION CHECK
Check the 50-tonne annual threshold:
- Below 50 tonnes/year → largely exempt from reporting and authorisation
  (exception: electricity and hydrogen remain in scope regardless of quantity)
- Above 50 tonnes/year → full CBAM compliance required
State the result clearly.

COST ESTIMATE
If CBAM applies and tonnage is provided, calculate the estimated CBAM cost:
- Formula: Embedded emissions (tCO2e) × EU ETS carbon price (€/tCO2e)
- Use the current EU ETS price (approximately €65/tCO2e as of 2026 — note
  this fluctuates; importers should check the live ETS price)
- If embedded emissions data is not provided, use default emission factors
  for the sector and state clearly that these are default values
- Show the calculation step by step

COMPLIANCE REQUIREMENTS
List what the importer must do:
1. Authorised CBAM Declarant status (required since 31 March 2026)
2. CBAM certificates — must hold 50% of embedded emissions per quarter
3. Annual CBAM declaration — due by 31 May each year
4. Embedded emissions data — from supplier (preferred) or default values
5. Verification — third-party verification required for actual emissions data

DOCUMENTATION CHECKLIST
List the specific documents required for this import.

KEY RISKS
2-3 bullet points on the main compliance risks for this specific case.

Rules:
- Always cite EU Regulation 2023/956
- Be precise about the 50-tonne threshold and sector coverage
- Never invent carbon prices — use the approximate figure and tell the
  importer to verify the live ETS price at https://ember-climate.org/data/
- If the product is not in a covered sector, say so clearly
- Output in plain Markdown
- Covered sectors: iron & steel, aluminium, cement, fertilizers,
  hydrogen, electricity
- Exempt countries: Iceland, Liechtenstein, Norway, Switzerland
  (have their own ETS linked to EU ETS)
""".strip()

agent = Agent(
    instructions=INSTRUCTIONS,
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),  # pragma: allowlist secret
    ),
    markdown=True,
)


# ---------------------------------------------------------------------------
# 2. Bindu configuration
# ---------------------------------------------------------------------------

config = {
    "author": "your.email@example.com",
    "name": "cbam_calculator",
    "description": (
        "An EU trade compliance agent that calculates Carbon Border Adjustment "
        "Mechanism (CBAM) obligations under EU Regulation 2023/956. Covers "
        "applicability checks, exemption thresholds, cost estimates, compliance "
        "requirements, and documentation checklists for EU importers of "
        "iron & steel, aluminium, cement, fertilizers, hydrogen, and electricity."
    ),
    "version": "1.0.0",
    "capabilities": {
        "compliance": ["cbam", "carbon-border-tax", "eu-regulation", "trade-compliance"],
        "calculation": ["carbon-cost", "ets-price", "embedded-emissions"],
        "research": ["exemption-check", "documentation-requirements"],
        "streaming": False,
    },
    "skills": ["skills/cbam-compliance-skill"],
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
}


# ---------------------------------------------------------------------------
# 3. Handler
# ---------------------------------------------------------------------------

def handler(messages: list[dict[str, str]]):
    """Calculate CBAM obligations for an EU importer.

    Args:
        messages: Standard A2A message list, e.g.
                  [{"role": "user", "content":
                    "Calculate CBAM cost for 200 tonnes of aluminium from Turkey"}]

    Returns:
        CBAM applicability, exemption check, cost estimate, compliance
        requirements, documentation checklist, and key risks.
    """
    try:
        user_messages = [m for m in messages if m.get("role") == "user"]
        if not user_messages:
            return (
                "No query received. Please describe your import, e.g. "
                "'Do I need CBAM for importing 200 tonnes of steel from China?'"
            )

        query = user_messages[-1].get("content", "").strip()
        if not query:
            return (
                "Empty query. Please describe your import situation, e.g. "
                "'Calculate CBAM cost for 200 tonnes of aluminium from Turkey'"
            )

        result = agent.run(input=messages)
        return result

    except Exception as e:
        return f"CBAM calculation error: {str(e)}"


# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("🌍 CBAM Carbon Calculator running at http://localhost:3773")
    print("♻️  Example: Calculate CBAM cost for 200 tonnes of aluminium from Turkey")
    bindufy(config, handler)
