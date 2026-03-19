"""The 'Look Ma, No Hands' Echo Agent"""
from bindu.penguin.bindufy import bindufy

def handler(messages):
    """
    I am a dumb agent. I don't know how to read files.
    I just echo whatever the Bindu framework hands me!
    """
    # If the framework did its job, this 'content' will contain the fully parsed PDF/TXT prompt.
    final_text = messages[-1].get("content", "[No content received]")
    
    return [{
        "role": "assistant", 
        "content": f"🤖 **NATIVE FRAMEWORK TEST:**\n\n{final_text}"
    }]

config = {
    "author": "tester@bindu.dev",
    "name": "dumb_echo_agent",
    "description": "Testing if the framework parses files natively.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"]
    },
    "skills": [],
}

bindufy(config, handler)