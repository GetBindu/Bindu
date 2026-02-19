"""Pause/Resume Test Agent — Designed to test task pause and resume operations.

This agent performs a long-running async task with progress updates,
making it ideal for testing pause/resume functionality.
"""

import asyncio
from bindu.penguin.bindufy import bindufy


async def handler(messages):
    """Process messages with a long-running async task.
    
    This handler simulates a multi-step process that takes time,
    allowing you to test pausing and resuming the task.
    
    Args:
        messages: List of message dictionaries containing conversation history.
        
    Returns:
        List containing assistant messages with progress updates.
    """
    user_input = messages[-1]["content"]
    
    # Parse number of steps from user input (default to 10)
    try:
        steps = int(user_input) if user_input.isdigit() else 10
        steps = min(max(steps, 5), 60)  # Clamp between 5 and 60
    except (ValueError, AttributeError):
        steps = 10
    
    responses = []
    
    # Initial response
    responses.append({
        "role": "assistant",
        "content": f"Starting {steps}-step async task. You can pause this at any time."
    })
    
    # Perform async work with progress updates
    for i in range(1, steps + 1):
        # Simulate async work (this can be paused!)
        await asyncio.sleep(2)  # 2 seconds per step
        
        # Progress update every few steps
        if i % 3 == 0 or i == steps:
            progress = (i / steps) * 100
            responses.append({
                "role": "assistant",
                "content": f"Step {i}/{steps} complete ({progress:.0f}%)"
            })
    
    # Final completion message
    responses.append({
        "role": "assistant",
        "content": f"All {steps} steps completed successfully!"
    })
    
    return responses


# Configuration
config = {
    "author": "bonderiddhish@gmail.com",
    "name": "pause_resume_test_agent",
    "description": "Agent designed for testing pause/resume operations with async tasks",
    "deployment": {"url": "http://localhost:3776", "expose": True},
    "skills": [],
}

bindufy(config, handler)
