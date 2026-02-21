# Healthcare Compliance Agent Example

This example demonstrates a compliance-first AI agent built on Bindu, designed for clinical decision support.

## Features
- **RAG-Grounded Reasoning**: Uses local clinical guidelines to eliminate hallucinations.
- **Collaborative A2A Reasoning**: Consults specialized sub-agents for complex neurological cases.
- **X402 Payments**: Implements a "Pay-per-query" model (0.05 USDC).
- **Immutable Audit Logging**: Every decision is logged with a trace ID and confidence score.

## Setup

1. **Install dependencies**:
   ```bash
   uv sync --dev
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Add your OpenRouter API key to .env
   ```

3. **Run the Agent**:
   ```bash
   uv run examples/healthcare-compliance-agent/main.py
   ```

## Interactive UI
A high-fidelity terminal simulator is included in the `ui/` directory. Open `ui/index.html` to see the compliance flow in a web interface.

## Protocols Included
Includes synthetic guidelines for:
- Hypertension, Diabetes, Asthma, Hyperlipidemia, Depression, ADHD, Autism, Alzheimer's, and Multiple Sclerosis.
