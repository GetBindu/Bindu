"""Slow Echo Agent - for testing pause/resume functionality."""

import asyncio
from bindu.penguin.bindufy import bindufy


async def handler(messages):
    """Handle messages with a delay to keep task in 'working' state."""
    # This async delay keeps the task in "working" state
    # without blocking the event loop, allowing pause/resume to work
    await asyncio.sleep(2)  # 2 seconds is enough to catch it
    return [{"role": "assistant", "content": messages[-1]["content"]}]


config = {
    "author": "test@example.com",
    "name": "slow_echo_agent",
    "description": "A slow echo agent for testing pause/resume",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
    },
}

bindufy(config, handler)
