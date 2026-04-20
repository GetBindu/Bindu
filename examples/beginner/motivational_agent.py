"""
Motivational Quote Agent - A simple agent that returns motivational quotes.
Based on the echo_simple_agent.py example.
"""

import os
import random
from bindu.penguin.bindufy import bindufy

# Collection of motivational quotes
QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "It does not matter how slowly you go as long as you do not stop. - Confucius",
    "Believe you can and you're halfway there. - Theodore Roosevelt",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "Success is not final, failure is not fatal: it is the courage to continue that counts. - Winston Churchill",
    "Your time is limited, don't waste it living someone else's life. - Steve Jobs",
    "The harder you work for something, the greater you'll feel when you achieve it.",
    "Dream it. Believe it. Build it.",
    "Start where you are. Use what you have. Do what you can.",
    "The only limit to our realization of tomorrow is our doubts of today.",
]

def get_motivational_quote():
    """Return a random motivational quote."""
    return random.choice(QUOTES)

def handler(messages):
    """Return a motivational quote for any message."""
    quote = get_motivational_quote()
    return [{
        "role": "assistant",
        "content": f"💪 Here's your motivation: {quote}"
    }]

config = {
    "author": "jerphinasmi24@gmail.com",
    "name": "motivational_agent",
    "description": "An agent that shares motivational quotes to brighten your day",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}

if __name__ == "__main__":
    bindufy(config, handler)
    print("✨ Motivational Quote Agent is running!")
    print("📢 Try sending a message to get inspired!")
