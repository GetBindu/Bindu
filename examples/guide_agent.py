from bindu.penguin.bindufy import bindufy

def handler(messages: list[dict[str, str]]):
    """
    An interactive guide for new Bindu users.
    """
    # Get the last message from the user
    user_input = messages[-1]["content"].lower() if messages else ""
    
    # Default welcome message if no input or first interaction
    if not user_input or user_input == "start":
        return [{
            "role": "assistant", 
            "content": (
                "👋 **Welcome to Bindu!** I'm your Onboarding Guide.\n\n"
                "I can help you get started. What would you like to do?\n\n"
                "1. **See an Example**: run a simple agent.\n"
                "2. **Read Docs**: find the documentation.\n"
                "3. **Learn Concepts**: understand Agents and Skills.\n\n"
                "Reply with **1**, **2**, or **3**."
            )
        }]

    # Option 1: Examples
    if "1" in user_input or "example" in user_input:
        return [{
            "role": "assistant",
            "content": (
                "✅ **Run a Simple Agent**\n\n"
                "To see Bindu in action, try the Echo Agent:\n"
                "```bash\n"
                "python examples/echo_agent.py\n"
                "```\n"
                "Then use `curl` to send it a message."
            )
        }]

    # Option 2: Docs
    if "2" in user_input or "docs" in user_input:
        return [{
            "role": "assistant",
            "content": (
                "📚 **Documentation**\n\n"
                "You can find the full documentation at:\n"
                "👉 [docs.getbindu.com](https://docs.getbindu.com)\n\n"
                "It covers everything from installation to advanced orchestration."
            )
        }]

    # Option 3: Concepts
    if "3" in user_input or "concept" in user_input:
        return [{
            "role": "assistant",
            "content": (
                "🧠 **Core Concepts**\n\n"
                "- **Agents**: Autonomous units that can communicate.\n"
                "- **Skills**: Capabilities an agent advertises (like 'pdf-processing').\n"
                "- **Bindu Protocol**: The language agents use to talk to each other.\n\n"
                "Check `skills/` directory for examples of agent capabilities."
            )
        }]

    # Fallback
    return [{
        "role": "assistant",
        "content": "I didn't quite get that. Reply with **1** (Examples), **2** (Docs), or **3** (Concepts)."
    }]

config = {
    "name": "onboarding_guide",
    "description": "An interactive assistant for new Bindu developers.",
    "deployment": {
        "url": "http://localhost:3773", 
        "expose": True
    },
    "skills": [],
    "version": "1.0.0",
    "author": "pallabsar001@gmail.com"
}

if __name__ == "__main__":
    print("🚀 Starting Onboarding Guide Agent...")
    print("Run this to interact with it via curl or other tools.")
    bindufy(config, handler)
