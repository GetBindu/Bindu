"""
ZK-Policy Agent Example
-----------------------
This agent demonstrates how to implement a specialized security agent within the Bindu framework.
It simulates a Zero-Knowledge Proof (ZKP) workflow where an agent verifies data compliance
without revealing the sensitive data itself.

Author: Baljot Singh
"""

import time
from bindu.penguin.bindufy import bindufy

# --- Simulation Logic ---


def generate_mock_zk_proof(content: str) -> dict:
    """
    Simulates the generation of a ZK-SNARK proof.

    In a production version (like ZK-Sentinel), this would utilize
    circom/snarkjs or a Python binding for a proving system.
    """
    # Simulate computation cost
    time.sleep(0.5)

    # Deterministic mock hash for "proof"
    proof_hash = hex(hash(content + "secret_salt"))[2:]

    return {
        "proof_scheme": "groth16-mock",
        "public_inputs": ["policy_hash_v1", len(content)],
        "proof": f"0x{proof_hash}...",
    }


def check_policy(content: str) -> bool:
    """Perform a simple policy check.

    Evaluates the provided proof against the current policy set.
    """
    forbidden_terms = ["TOP SECRET", "CLASSIFIED", "PRIVATE KEY"]
    return not any(term in content for term in forbidden_terms)


# --- Bindu Handler ---


def handler(messages: list[dict[str, str]]):
    """Intercept the request and check the policy.

    The main entry point for processing incoming agent requests.
    """
    # Defensive check for empty history
    if not messages:
        return [{"role": "assistant", "content": "Ready for verification."}]

    last_user_message = messages[-1].get("content", "")

    # 1. Verify Compliance
    is_compliant = check_policy(last_user_message)

    if not is_compliant:
        return [
            {
                "role": "assistant",
                "content": "❌ BLOCK: Message contains forbidden content. Policy verification failed.",
            }
        ]

    # 2. Generate Proof (The "Founder Energy" touch)
    proof = generate_mock_zk_proof(last_user_message)

    response_body = (
        f"✅ **Verified**: Content matches safety policy.\n\n"
        f"**ZK-Proof Generated:**\n"
        f"`{proof['proof']}`\n\n"
        f"*(This agent demonstrates how Bindu can integrate with privacy protocols like ZK-Sentinel)*"
    )

    return [{"role": "assistant", "content": response_body}]


# --- Configuration ---

config = {
    "author": "baljots1000@gmail.com",
    "name": "zk_policy_agent",
    "description": "A security agent that provides proofs of policy compliance.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    # Link to the skill we defined in Step 2
    "skills": ["skills/zk-policy"],
}

if __name__ == "__main__":
    # Start the agent
    bindufy(config, handler)
