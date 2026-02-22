import logging
from bindu.penguin.bindufy import bindufy

# Set up observability 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("EscrowAgent")

def escrow_handler(messages):
    """
    The core logic of the Escrow Arbiter.
    Because this method is protected by X402, this code ONLY executes 
    after the Bindu network verifies the USDC payment on-chain.
    """
    logger.info("Payment verified by Bindu network. Executing escrow release.")
    
    # In a real scenario, this would evaluate the 'messages' to verify work proof
    last_message = messages[-1]["content"]
    
    if "proof" in last_message.lower():
        return [{"role": "assistant", "content": "Proof verified. Escrow condition met. Transaction settled."}]
    else:
        return [{"role": "assistant", "content": "Insufficient proof provided. Funds remain locked."}]

# Bindu X402 Native Configuration
# This dictates the agent's identity, deployment, and payment requirements.
config = {
    "author": "your.email@example.com", # TODO: Put your email here
    "name": "escrow_arbiter",
    "description": "An automated escrow agent that verifies proof of work before settling transactions.",
    "deployment": {
        "url": "http://localhost:3773", 
        "expose": True
    },
    # This is what gets you hired: Native use of their X402 configuration
    "execution_cost": {
        "amount": "$5.00",                  # Amount required to trigger the agent
        "token": "USDC",                    # Token type
        "network": "base-sepolia",          # Testnet for safe development
        "pay_to_address": "0xf7a61E533Bd41B516258Fa8195463649AFe6107f",  # TODO: Paste your MetaMask address
        "protected_methods": [
            "message/send"                  # Gating the primary communication method
        ]
    },
    "skills": []
}

# Bindufy wraps your logic into a living microservice connected to the Internet of Agents
if __name__ == "__main__":
    logger.info("Starting Escrow Arbiter on the Bindu network...")
    bindufy(config, escrow_handler)