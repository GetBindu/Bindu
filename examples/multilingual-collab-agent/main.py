# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Multilingual Collaborative Agent v2 — A Bindu Agent.

An identity-aware agent that detects user language (English, Hindi, Bengali)
and responds in the same language. Supports research, translation, and
collaborative workflows using Bindu DID identity and Mem0 persistent memory.
"""

import asyncio
import json
import os
from pathlib import Path
from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.mem0 import Mem0Tools
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global agent instance — initialized lazily on first request
agent: Agent | None = None
_initialized = False
_init_lock = asyncio.Lock()


def load_config() -> dict:
    """Load agent configuration from agent_config.json."""
    config_path = Path(__file__).parent / "agent_config.json"
    with open(config_path, "r") as f:
        return json.load(f)


def build_agent() -> Agent:
    """Build and return the multilingual agent instance."""
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    mem0_api_key = os.getenv("MEM0_API_KEY")
    model_name = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

    if not openrouter_api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is required.")
    if not mem0_api_key:
        raise ValueError(
            "MEM0_API_KEY environment variable is required. "
            "Get your key from: https://app.mem0.ai/dashboard/api-keys"
        )

    tools = [DuckDuckGoTools()]
    try:
        tools.append(Mem0Tools(api_key=mem0_api_key))
    except Exception as e:
        print(f"⚠️  Mem0 tools unavailable: {e}. Continuing without memory.")

    return Agent(
        name="multilingual-collab-agent-v2",
        model=OpenRouter(
            id=model_name,
            api_key=openrouter_api_key,
        ),
        tools=tools,
        instructions=dedent("""\
            You are a multilingual research and collaboration agent built on the
            Bindu framework — part of the Internet of Agents.

            ## Language Detection and Response

            ALWAYS detect the language of the user's message and respond in that
            same language. Follow these rules strictly:

            - If the message is in **English** → respond entirely in English
            - If the message is in **Hindi** (हिन्दी) → respond entirely in Hindi
            - If the message is in **Bengali** (বাংলা) → respond entirely in Bengali
            - If the message mixes languages → respond in the dominant language
            - If unsure → default to English

            Never switch languages mid-response. Never explain that you detected
            a language — just respond naturally in that language.

            ## Capabilities

            ### Research
            - Search the web using DuckDuckGo for current information
            - Summarize findings clearly and concisely
            - Cite sources when available
            - Handle research queries in any supported language

            ### Translation
            - Translate text between English, Hindi, and Bengali
            - Preserve the meaning, tone, and context of the original
            - For technical terms with no direct translation, keep the
              original term and provide a brief explanation

            ### Collaboration
            - Help users draft messages, emails, or documents in any language
            - Assist with cross-language communication between users
            - Provide cultural context when relevant

            ### Memory
            - Remember important facts from previous conversations using Mem0
            - Reference past interactions when relevant
            - Build a knowledge base about the user's preferences and context

            ## Identity

            You are an identity-aware agent with a Bindu DID (Decentralized
            Identifier). This means you can be discovered and called by other
            agents in the Internet of Agents ecosystem.

            ## Response Style

            - Be concise and direct
            - Use bullet points for lists and steps
            - Format code in code blocks
            - Match the formality level of the user's message
            - For Hindi and Bengali responses, use proper script
              (Devanagari for Hindi, Bengali script for Bengali)

            ## Example Interactions

            User (English): "What is the Bindu framework?"
            → Respond in English with a clear explanation

            User (Hindi): "बिंदू फ्रेमवर्क क्या है?"
            → Respond entirely in Hindi: "बिंदू एक AI एजेंट फ्रेमवर्क है..."

            User (Bengali): "বিন্দু ফ্রেমওয়ার্ক কী?"
            → Respond entirely in Bengali: "বিন্দু হল একটি AI এজেন্ট ফ্রেমওয়ার্ক..."
        """),
        add_datetime_to_context=True,
        markdown=True,
    )


async def handler(messages: list[dict[str, str]]) -> Any:
    """Handle incoming messages — initializes agent lazily on first call.

    Args:
        messages: List of message dicts with 'role' and 'content' keys.

    Returns:
        Agent response string.
    """
    global agent, _initialized

    async with _init_lock:
        if not _initialized:
            print("🔧 Initializing multilingual agent...")
            agent = build_agent()
            _initialized = True
            print("✅ Agent initialized")

    response = await agent.arun(messages)
    return response


def main() -> None:
    """Start the Bindu agent server."""
    config = load_config()
    print("🌍 Starting Multilingual Collaborative Agent...")
    print(f"   Supported languages: English, Hindi (हिन्दी), Bengali (বাংলা)")
    print(f"   Model: {os.getenv('MODEL_NAME', 'openai/gpt-4o-mini')}")
    print(f"   Memory: Mem0 persistent memory enabled")
    bindufy(config, handler)


if __name__ == "__main__":
    main()
