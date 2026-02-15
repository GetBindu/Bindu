# Autonomous Multi-Agent Trading Desk 

This example demonstrates how to use a central identity and payment ledger (simulating the Bindu Hub) to facilitate trustless data exchange between multiple AI agents. 

Rather than a single script executing tasks sequentially, this architecture features three distinct agents running concurrently, discovering each other via a central registry, and exchanging mock tokens for services.



## The Architecture

1. **Bindu Hub (`hub.py`)**: The foundation. It hosts the `/registry` for agents to announce their capabilities and the `/ledger` to handle micro-transactions.
2. **Sentiment Agent (`agent_sentiment.py`)**: A seller. It registers with the Hub and charges 5 tokens to analyze market sentiment for a given asset.
3. **Quant Agent (`agent_quant.py`)**: A seller. It registers with the Hub and charges 10 tokens to calculate statistical edges (volatility, moving averages) on market data.
4. **Portfolio Manager (`agent_manager.py`)**: The buyer. It receives a starting budget from the Hub, dynamically discovers the two sellers, pays them via the ledger, and synthesizes a final trading decision.

## Requirements

Ensure you have the following dependencies installed:
`pip install fastapi uvicorn httpx pandas numpy`

## How to Run the Network

To simulate the decentralized network, you need to spin up each component on its own port. Open four separate terminal instances and run:

**Terminal 1 (The Hub):**
`uvicorn hub:app --port 8000`

**Terminal 2 (Sentiment Agent):**
`uvicorn agent_sentiment:app --port 8001`

**Terminal 3 (Quant Agent):**
`uvicorn agent_quant:app --port 8002`

**Terminal 4 (Portfolio Manager):**
`uvicorn agent_manager:app --port 8003`

## Triggering the Workflow

Once all four servers are running, trigger the Portfolio Manager to begin its research phase by visiting the following URL in your browser or via curl:

`http://localhost:8003/execute_research?asset=hyperliquid`

You will receive a synthesized JSON response containing the final decision and the purchased intelligence from both sub-agents.