# 🌍 CBAM Carbon Calculator

A Bindu trade compliance agent that calculates Carbon Border Adjustment
Mechanism (CBAM) obligations for EU importers under EU Regulation 2023/956.

CBAM entered its definitive phase on **1 January 2026**. EU importers of
covered goods must now purchase and surrender CBAM certificates proportional
to the embedded carbon emissions in their imports — or face blocked shipments
and fines.

## Covered Sectors

| Sector | HS Chapters |
|---|---|
| Iron & Steel | 72, 73 |
| Aluminium | 76 |
| Cement | 25 |
| Fertilizers | 31 |
| Hydrogen | 2804.10 |
| Electricity | 2716.00 |

## Features

- Checks whether CBAM applies to your product and origin country
- Applies the 50-tonne annual exemption threshold
- Estimates CBAM certificate cost using embedded emissions × EU ETS price
- Uses sector default emission factors when supplier data is unavailable
- Lists Authorised CBAM Declarant requirements
- Generates a documentation checklist for your specific import
- Flags key compliance risks

## Output Format

```text
CBAM APPLICABILITY
Whether CBAM applies, with CN code reference.

EXEMPTION CHECK
50-tonne threshold result — exempt or full compliance required.

COST ESTIMATE
Step-by-step calculation: emissions × ETS price = certificate cost.

COMPLIANCE REQUIREMENTS
What you must do: declarant status, certificates, annual declaration.

DOCUMENTATION CHECKLIST
Specific documents required for this import.

KEY RISKS
Main compliance risks for your specific case.
```

## Setup

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env

uv add bindu agno python-dotenv
python cbam_calculator.py
```

The agent runs at `http://localhost:3773`.

## Example Queries

```text
Do I need CBAM for importing steel pipes from China?
Calculate CBAM cost for 200 tonnes of aluminium from Turkey
Am I exempt from CBAM if I import 30 tonnes of cement per year?
What documents do I need to import fertilizers from Egypt into the EU?
Is CBAM applicable for hydrogen imports from Saudi Arabia?
```

## Key Dates

| Date | Event |
|---|---|
| 1 Oct 2023 | Transitional phase began (reporting only) |
| 1 Jan 2026 | Definitive phase — financial liability starts |
| 31 Mar 2026 | Deadline for Authorised CBAM Declarant registration |
| 31 May 2026 | First annual CBAM declaration due |
| 2026–2034 | Free ETS allowances gradually phased out |

## Exempt Countries

Iceland, Liechtenstein, Norway, and Switzerland are exempt — they have
their own ETS systems linked to the EU ETS.

## Project Structure

```text
cbam-calculator/
├── cbam_calculator.py                 # Main agent + bindufy()
├── .env.example                       # Environment variables
├── skills/
│   └── cbam-compliance-skill/
│       └── skill.yaml                 # Skill definition
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `BINDU_DEPLOYMENT_URL` | No | Override default `http://localhost:3773` |

## Disclaimer

This agent provides general guidance only and does not constitute legal or
tax advice. CBAM obligations depend on specific product characteristics,
verified emissions data, and current EU ETS prices. Always consult a licensed
customs broker or trade compliance specialist before filing CBAM declarations.

Reference: EU Regulation 2023/956 — https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32023R0956
