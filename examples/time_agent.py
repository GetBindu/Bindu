from datetime import datetime
from bindu.penguin.bindufy import bindufy

def handler(messages):
    """Handle incoming messages by replying with the current time."""
    
    # Get the current time in HH:MM:SS format
    current_time = datetime.now().strftime("%H:%M:%S")
    
    # Return the response in the format Bindu expects
    return [{"role": "assistant", "content": f"The current time is: {current_time}"}]


# Configuration
config = {
    # You can keep this email or change it to yours if you want!
    "author": "gaurikasethi88@gmail.com", 
    "name": "time_agent",
    "description": "A simple agent that tells you the current time.",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": [],
}

# Run the agent
bindufy(config, handler)