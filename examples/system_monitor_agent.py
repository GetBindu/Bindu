"""System Monitor Agent example for Bindu.

This agent demonstrates how to create a custom 'Skill' for monitoring system health.
"""

import os
import psutil
import platform
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

# 1. Load environment variables (like API keys)
load_dotenv()

# 2. Define our actual hardware lookup 'Tool'
def get_system_health(metrics: list[str] = ["all"]) -> dict:
    """Retrieves system health metrics.
    Args:
        metrics: List of metrics to fetch ('cpu', 'memory', 'disk', 'platform', 'all')
    """
    results = {}
    
    if "cpu" in metrics or "all" in metrics:
        results["cpu_percent"] = psutil.cpu_percent(interval=1)
        results["cpu_count_logical"] = psutil.cpu_count()
        results["cpu_count_physical"] = psutil.cpu_count(logical=False)

    if "memory" in metrics or "all" in metrics:
        mem = psutil.virtual_memory()
        results["memory_used_gb"] = round(mem.used / (1024**3), 2)
        results["memory_total_gb"] = round(mem.total / (1024**3), 2)
        results["memory_percent"] = mem.percent

    if "disk" in metrics or "all" in metrics:
        disk = psutil.disk_usage('/')
        results["disk_used_gb"] = round(disk.used / (1024**3), 2)
        results["disk_total_gb"] = round(disk.total / (1024**3), 2)
        results["disk_percent"] = disk.percent

    if "platform" in metrics or "all" in metrics:
        results["os"] = platform.system()
        results["os_release"] = platform.release()
        results["architecture"] = platform.machine()

    if "battery" in metrics or "all" in metrics:
        battery = psutil.sensors_battery()
        if batery:
            results["battery_percent"] = battery.percent
            results["power_plugged"] = battery.power_plugged
        else:
            results["battery_percent"] = "No battery detected (Desktop?)"

    return results

# 3. Create our Agent (using Agno framework)
agent = Agent(
    name="system_monitor",
    description="I monitor hardware health and system metrics.",
    instructions=[
        "You are a specialized System Administrator agent.",
        "Your goal is to provide accurate hardware metrics when asked.",
        "Synthesize the data into a clear, readable summary for the user.",
        "If multiple metrics are requested, present them in a clean list format."
    ],
    # We use a placeholder or local model if no API key is provided
    # For this example, we assume OpenRouter or OpenAI is configured
    model=OpenAIChat(id="gpt-4o-mini"), 
    tools=[get_system_health],
    show_tool_calls=True
)

# 4. Bindu Configuration
config = {
    "author": "your.email@example.com",
    "name": "system_monitor_agent",
    "description": "An agent that monitors system hardware health.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True
    },
    # POINTING TO OUR NEW SKILL
    "skills": ["examples/skills/system-info"] 
}

# 5. The Handler (The Bridge)
def handler(messages: list[dict]):
    """Process incoming Bindu messages and return the agent's response."""
    # agno agents take input as a string or message list
    result = agent.run(input=messages)
    return result

# 6. Launch it!
if __name__ == "__main__":
    print("🚀 Starting System Monitor Agent...")
    print("📍 Skill advertised: System Monitor (system-info-v1)")
    bindufy(config, handler)
