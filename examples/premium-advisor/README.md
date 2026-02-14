# Premium Market Insight Advisor

A premium Bindu agent that provides high-value market insights and financial analysis with X402 payment gating. This example demonstrates how to create paid agents using Bindu's payment infrastructure.

## What is This?

This is a **premium market insight advisor** that:
- Provides proprietary deep-chain market analysis
- Offers investment recommendations and risk assessments
- Requires X402 payment (0.01 USDC) per interaction
- Uses Agno framework with OpenRouter's `openai/gpt-oss-120b` model
- Demonstrates payment-gated AI services

## Features

- **X402 Payment Integration**: Secure payment processing (0.01 USDC per query)
- **Market Analysis**: Deep-chain analysis of blockchain projects
- **Investment Insights**: Actionable recommendations with risk assessments
- **Developer Activity Tracking**: Analysis of project fundamentals
- **Premium Content**: High-value insights that justify the cost
- **Agno Framework**: Modern AI agent architecture

## Quick Start

### Prerequisites
- Python 3.12+
- OpenRouter API key
- uv package manager
- Bindu installed in project root
- USDC on Base Sepolia for testing payments

### 1. Set Environment Variables

Create `.env` file in `examples/premium-advisor/`:

```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Install Dependencies

```bash
# From Bindu root directory
uv sync
```

### 3. Start the Premium Advisor

```bash
# From Bindu root directory
cd examples/premium-advisor
uv run python premium_advisor.py
```

The agent will start on `http://localhost:3773`

### 4. Test the Agent

Open your browser to `http://localhost:3773/docs` and use the chat interface, or:

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "What are the best investment opportunities right now?"}],
        "kind": "message",
        "messageId": "msg-001",
        "contextId": "ctx-001",
        "taskId": "task-001"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "1"
  }'
```

## Architecture

### File Structure

- **`premium_advisor.py`** - Main Agno agent with X402 payment integration
- **`skills/premium-market-insight-skill/`** - Bindu skill definition
- **`.env.example`** - Environment variable template
- **`README.md`** - This documentation

### Agent Configuration

```python
config = {
    "author": "premium.advisor@example.com",
    "name": "Oracle_of_Value",
    "description": "I provide high-value market insights. Payment required upfront.",
    "execution_cost": {
        "amount": "0.01",           # Cost per interaction
        "token": "USDC",           # Payment currency
        "network": "base-sepolia",  # Blockchain network
        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    },
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/premium-market-insight-skill"]
}
```

### Payment Flow

1. **User sends message** → Bindu receives request
2. **Payment check** → X402 validates 0.01 USDC payment
3. **Payment processed** → Funds transferred to specified address
4. **Agent execution** → Agno agent processes the request
5. **Premium response** → High-quality market insights returned

## Skills Integration

The agent includes a Bindu skill definition with:

- **Skill ID**: `premium-market-insight-skill`
- **Capabilities**: Market analysis, investment recommendations, risk assessment
- **Payment**: X402-gated premium service
- **Tags**: finance, market-analysis, investment, cryptocurrency, premium

## Example Interactions

### Sample Query
```
"What's your outlook for DeFi projects this quarter?"
```

### Premium Response
```
🔮 **Quarterly DeFi Outlook** 🔮

Based on deep-chain analysis:

**🟢 Accumulate:**
- Projects with >50% developer activity increase
- Protocols with completed audits and transparent governance
- Yield aggregators with diversified strategies

**🔴 Avoid:**
- Anonymous teams with no GitHub activity
- Projects promising unrealistic APYs (>100%)
- Protocols without insurance or safety mechanisms

**💡 Strategy:**
- DCA into blue-chip DeFi (Aave, Compound, Uniswap)
- Allocate 20% to emerging protocols with strong fundamentals
- Maintain 30% stablecoins for volatility management

Risk Score: 6/10 (Moderate - Market volatility remains high)
```

## Development

### Modifying the Agent

1. **Change instructions**: Edit the `Agent` instructions in `premium_advisor.py`
2. **Adjust pricing**: Modify `execution_cost` in the config
3. **Update skills**: Edit `skills/premium-market-insight-skill/skill.yaml`
4. **Change model**: Update `OpenRouter(id="...")` parameter

### Adding New Capabilities

```python
# Add new tools to the agent
from agno.tools.custom import custom_tool

@custom_tool
def analyze_token(token_address: str) -> str:
    """Analyze a specific token"""
    # Your analysis logic here
    return analysis_result

agent = Agent(
    instructions="...",
    model=OpenRouter(id="openai/gpt-oss-120b"),
    tools=[analyze_token],
)
```

## Testing Payments

### Setting Up Test Environment

1. **Get USDC on Base Sepolia**:
   - Use Base Sepolia faucet
   - Bridge from Ethereum Sepolia if needed

2. **Configure Wallet**:
   - Ensure your wallet has Base Sepolia network
   - Check USDC balance: `0.01 USDC` minimum per query

3. **Test Payment Flow**:
   - Send a message to the agent
   - Confirm payment prompt appears
   - Complete payment transaction
   - Receive premium insights

## Dependencies

All dependencies are managed through the root `pyproject.toml`:

```bash
# Core dependencies already included in bindu project
agno>=2.4.8
langchain>=1.2.9
langchain-openai>=1.1.8
python-dotenv>=1.1.0
```

## Security Considerations

- **Payment Validation**: All payments validated through X402 protocol
- **Private Keys**: Never store private keys in the code
- **API Keys**: Use environment variables for sensitive data
- **Network Security**: Test on Base Sepolia before mainnet deployment

## Troubleshooting

### Common Issues

1. **Payment Fails**:
   - Check USDC balance on Base Sepolia
   - Verify network configuration in wallet
   - Ensure correct pay_to_address

2. **Agent Not Responding**:
   - Verify OPENROUTER_API_KEY is set
   - Check agent logs for errors
   - Ensure port 3773 is available

3. **Environment Issues**:
   - Run `uv sync` from project root
   - Check Python version (3.12+)
   - Verify all dependencies installed

## Contributing

To extend this example:

1. **Add new analysis tools** in the agent
2. **Modify payment structure** for different tiers
3. **Update skill definition** with new capabilities
4. **Improve documentation** and examples

## License

This example is part of the Bindu framework and follows the same license terms.
