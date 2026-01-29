"""A premium agent example that demonstrates X402 payment gating."""

from bindu.penguin.bindufy import bindufy


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Provide premium market insights.

    This handler is protected by the X402 paywall.
    """
    advice = (
        "🔮 **Premium Market Insight** 🔮\n\n"
        "Based on our proprietary deep-chain analysis:\n"
        "- **Accumulate**: Assets with high developer activity.\n"
        "- **Avoid**: Projects with anonymous founders and no audit.\n"
        "- **Strategy**: Dollar-Cost Average (DCA) is your best friend in this volatility."
    )

    return [{"role": "assistant", "content": advice}]


config = {
    "author": "premium.advisor@example.com",
    "name": "Oracle_of_Value",
    "description": "I provide high-value market insights. Payment required upfront.",
    "execution_cost": {
        "amount": "0.01",  # Cost of one interaction
        "token": "USDC",  # Currency
        "network": "base-sepolia",  # Network (Base Testnet)
        "pay_to_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Dummy ETH Address
    },
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "debug_mode": True,
}

if __name__ == "__main__":
    print("Starting Premium Advisor Agent...")
    print(
        f"Cost: {config['execution_cost']['amount']} {config['execution_cost']['token']}"
    )
    print("URL: http://localhost:3773")
    bindufy(config, handler)
