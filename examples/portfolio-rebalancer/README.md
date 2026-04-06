# Portfolio Rebalancer Agent (Bindu Multi-Agent)

A multi-agent system that analyzes portfolio allocation, evaluates risk, and generates rebalancing actions using semantic memory.


##  Architecture

The system is composed of four specialized agents:
- **Analyst** → Computes current allocation and drift from target
- **Pricer** → Fetches asset prices (CoinGecko with fallback)
- **Risk** → Evaluates asset-level and portfolio-level risk
- **Rebalancer** → Generates trade actions based on drift and risk

All agents are orchestrated through a central handler and share a semantic memory layer.


## Features

- Multi-agent architecture with clear separation of concerns  
- Structured data flow between agents  
- Risk-aware trade decision making  
- Partial rebalancing strategy (avoids aggressive full liquidation)  
- Semantic memory for stateful behavior  
- External price integration with fallback  



##  Run

```bash
python portfolio_rebalancer_agent.py
```


## Example
Input
```json
{
  "portfolio": {
    "id": "demo-1",
    "assets": [
      {"symbol": "BTC", "current_value": 6000},
      {"symbol": "ETH", "current_value": 4000}
    ]
  },
  "target": {
    "BTC": 50,
    "ETH": 50
  }
}
```

Output
```json
{
  "portfolio_id": "demo-1",
  "actions": [
    {
      "symbol": "BTC",
      "action": "sell",
      "amount_usd": 1500,
      "reason": "BTC drift +10.0% (25% rebalance)"
    },
    {
      "symbol": "ETH",
      "action": "buy",
      "amount_usd": 1500,
      "reason": "ETH drift -10.0% (25% rebalance)"
    }
  ],
  "summary": "Rebalance by selling $1,500 and buying $1,500. Moderate portfolio risk"
}
```

## Notes
- Trade amounts represent partial rebalancing (~25%), not full liquidation
- Risk scores influence decision-making and can adjust trade sizes
- Designed for clarity and extensibility rather than trading precision

## Structure
```bash
examples/portfolio-rebalancer/
├── portfolio_rebalancer_agent.py
├── agents/
│   ├── analyst.py
│   ├── pricer.py
│   ├── risk.py
│   └── rebalancer.py
├── shared/
│   ├── types.py
│   └── memory.py
├── skills/
│   └── portfolio-rebalancer-agent-skill/
│       └── skill.yaml
```

## Summary

This example demonstrates how multiple agents can collaborate to:
- analyze portfolio state
- evaluate risk
- generate explainable actions

while maintaining a clean and modular architecture.