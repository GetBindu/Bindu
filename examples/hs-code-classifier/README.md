# 🛃 HS Code Classifier

A Bindu trade compliance agent that classifies any product into its correct
6-digit Harmonized System (HS) code — the international standard used by
customs authorities in every country to identify goods crossing borders.

Getting the HS code wrong means wrong tariffs, blocked shipments, or fines.
This agent helps SMBs get it right without hiring a trade lawyer.

## Features

- Accepts any product description in plain English
- Returns the correct 6-digit HS code with WCO chapter heading
- Explains the classification rationale with chapter/heading/subheading references
- Provides indicative duty rates for China→EU, India→EU, China→US, India→US
- Flags common misclassification risks and required documentation
- Identifies preferential trade agreements (GSP, FTA) that may reduce duty
- Lists alternative HS codes with conditions for when each applies
- Asks clarifying questions when the product description is ambiguous

## Output Format

```text
HS CODE
6109.10 — T-shirts, singlets and other vests, of cotton

CLASSIFICATION RATIONALE
Why this code applies, with chapter/heading/subheading references.

DUTY RATES
Table of indicative MFN rates for common SMB trade routes.

COMPLIANCE NOTES
Misclassification risks, trade agreements, required documentation.

ALTERNATIVE CODES
Other codes that could apply depending on product specifications.
```

## Setup

```bash
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env

uv add bindu agno python-dotenv
python hs_code_classifier.py
```

The agent runs at `http://localhost:3773`.

## Example Queries

```text
Classify cotton t-shirts for adults
What HS code for lithium-ion batteries used in laptops?
HS code for green coffee beans from Ethiopia
Classify unroasted arabica coffee, not decaffeinated
What code for stainless steel kitchen knives?
```

## Project Structure

```text
hs-code-classifier/
├── hs_code_classifier.py              # Main agent + bindufy()
├── .env.example                       # Environment variables
├── skills/
│   └── hs-classification-skill/
│       └── skill.yaml                 # Skill definition
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key |
| `BINDU_DEPLOYMENT_URL` | No | Override default `http://localhost:3773` |

## Disclaimer

Duty rates provided are indicative MFN rates only. Always verify against
the official tariff schedule of the importing country before filing a
customs declaration. For complex classifications, consult a licensed
customs broker or trade compliance specialist.

## Why This Matters

Every product crossing an international border needs an HS code. Get it
wrong and you face:

- **Wrong tariff rates** — overpaying or underpaying duty
- **Blocked shipments** — customs holds your goods pending reclassification
- **Fines** — penalties for incorrect declarations
- **Delays** — Rotterdam container dwell averaged 9.1 days in 2025 vs a
  normal 3, largely due to compliance failures

This agent is part of Bindu's trade compliance toolchain — a swarm of
agents helping SMBs navigate global trade without eye-watering legal bills.
