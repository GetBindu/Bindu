"""Research Agent - AI investigative journalism agent."""

# research_agent/main.py
import argparse
import asyncio
import json
import os
import sys
import traceback
from pathlib import Path
from textwrap import dedent
from typing import Any

from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.models.openrouter import OpenRouter
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.newspaper4k import Newspaper4kTools
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Global agent instance
agent: Agent | None = None
_initialized = False
_init_lock = asyncio.Lock()


def load_config() -> dict:
    """Load agent configuration from project root."""
    # Try multiple possible locations for agent_config.json
    possible_paths = [
        Path(__file__).parent.parent / "agent_config.json",  # Project root
        Path(__file__).parent / "agent_config.json",  # Same directory as main.py
        Path.cwd() / "agent_config.json",  # Current working directory
    ]

    for config_path in possible_paths:
        if config_path.exists():
            try:
                with open(config_path) as f:
                    return json.load(f)
            except (PermissionError, json.JSONDecodeError) as e:
                print(f"⚠️  Error reading {config_path}: {type(e).__name__}")
                continue
            except Exception as e:
                print(f"⚠️  Unexpected error reading {config_path}: {type(e).__name__}")
                continue

    # If no config found or readable, create a minimal default
    print("⚠️  No agent_config.json found, using default configuration")
    return {
        "name": "research-agent",
        "description": "AI research agent for investigative journalism",
        "version": "1.0.0",
        "deployment": {
            "url": "http://127.0.0.1:3773",
            "expose": True,
            "protocol_version": "1.0.0",
            "proxy_urls": ["127.0.0.1"],
            "cors": {
  "allow_origins": ["*"],
  "allow_methods": ["*"],
  "allow_headers": ["*"]
}

        },
        "environment_variables": [
            {"key": "OPENAI_API_KEY", "description": "OpenAI API key for LLM calls", "required": False},
            {"key": "OPENROUTER_API_KEY", "description": "OpenRouter API key for LLM calls", "required": False},
        ],
    }


async def initialize_agent() -> None:
    """Initialize the research agent with proper model and tools."""
    global agent

    # Get API keys from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    model_name = os.getenv("MODEL_NAME", "openai/gpt-4o")

    # Model selection logic (supports both OpenAI and OpenRouter)
    if openai_api_key:
        model = OpenAIChat(id="gpt-4o", api_key=openai_api_key)
        print("✅ Using OpenAI GPT-4o")
    elif openrouter_api_key:
        model = OpenRouter(
            id=model_name,
            api_key=openrouter_api_key,
            cache_response=True,
            supports_native_structured_outputs=True,
        )
        print(f"✅ Using OpenRouter model: {model_name}")
    else:
        # Define error message separately to avoid TRY003
        error_msg = (
            "No API key provided. Set OPENAI_API_KEY or OPENROUTER_API_KEY environment variable.\n"
            "For OpenRouter: https://openrouter.ai/keys\n"
            "For OpenAI: https://platform.openai.com/api-keys"
        )
        raise ValueError(error_msg)

    # Initialize tools
    search_tools = DuckDuckGoTools()
    newspaper_tools = Newspaper4kTools()

    # Create the research agent
    agent = Agent(
        name="Research Agent",
        model=model,
        tools=[search_tools, newspaper_tools],
        description=dedent("""\
            You are an elite investigative journalist with decades of experience at the New York Times.
            Your expertise encompasses: 📰

            - Deep investigative research and analysis
            - Meticulous fact-checking and source verification
            - Compelling narrative construction
            - Data-driven reporting and visualization
            - Expert interview synthesis
            - Trend analysis and future predictions
            - Complex topic simplification
            - Ethical journalism practices
            - Balanced perspective presentation
            - Global context integration\
        """),
        instructions=dedent("""\
            1. Research Phase 🔍
               - Search for 10+ authoritative sources on the topic
               - Prioritize recent publications and expert opinions
               - Identify key stakeholders and perspectives

            2. Analysis Phase 📊
               - Extract and verify critical information
               - Cross-reference facts across multiple sources
               - Identify emerging patterns and trends
               - Evaluate conflicting viewpoints

            3. Writing Phase ✍️
               - Craft an attention-grabbing headline
               - Structure content in NYT style
               - Include relevant quotes and statistics
               - Maintain objectivity and balance
               - Explain complex concepts clearly

            4. Quality Control ✓
               - Verify all facts and attributions
               - Ensure narrative flow and readability
               - Add context where necessary
               - Include future implications

            Always:
            - Cite your sources properly
            - Present balanced viewpoints
            - Flag any unverified information
            - Structure output professionally\
        """),
        expected_output=dedent("""\
            # {Compelling Headline} 📰

            ## Executive Summary
            {Concise overview of key findings and significance}

            ## Background & Context
            {Historical context and importance}
            {Current landscape overview}

            ## Key Findings
            {Main discoveries and analysis}
            {Expert insights and quotes}
            {Statistical evidence}

            ## Impact Analysis
            {Current implications}
            {Stakeholder perspectives}
            {Industry/societal effects}

            ## Future Outlook
            {Emerging trends}
            {Expert predictions}
            {Potential challenges and opportunities}

            ## Expert Insights
            {Notable quotes and analysis from industry leaders}
            {Contrasting viewpoints}

            ## Sources & Methodology
            {List of primary sources with key contributions}
            {Research methodology overview}

            ---
            Research conducted by AI Investigative Journalist
            New York Times Style Report
            Published: {current_date}
            Last Updated: {current_time}\
        """),
        add_datetime_to_context=True,
        markdown=True,
    )
    print("✅ Research Agent initialized")


async def run_agent(messages: list[dict[str, str]]) -> Any:
    """Run the agent with the given messages."""
    global agent
    if not agent:
        # Define error message separately to avoid TRY003
        error_msg = "Agent not initialized"
        raise RuntimeError(error_msg)

    # Run the agent and get response
    response = await agent.arun(messages)
    return response


async def handler(messages: list[dict[str, str]]) -> Any:
    """Handle incoming agent messages with lazy initialization."""
    global _initialized

    # Lazy initialization on first call
    async with _init_lock:
        if not _initialized:
            print("🔧 Initializing Research Agent...")
            await initialize_agent()
            _initialized = True

    # Run the async agent
    result = await run_agent(messages)
    return result


async def cleanup() -> None:
    """Clean up any resources."""
    print("🧹 Cleaning up Research Agent resources...")


def main():
    """Run the main entry point for the Research Agent."""
    parser = argparse.ArgumentParser(description="Bindu Research Agent")
    parser.add_argument(
        "--openai-api-key",
        type=str,
        default=os.getenv("OPENAI_API_KEY"),
        help="OpenAI API key (env: OPENAI_API_KEY)",
    )
    parser.add_argument(
        "--openrouter-api-key",
        type=str,
        default=os.getenv("OPENROUTER_API_KEY"),
        help="OpenRouter API key (env: OPENROUTER_API_KEY)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("MODEL_NAME", "openai/gpt-4o"),
        help="Model ID for OpenRouter (env: MODEL_NAME)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Path to agent_config.json (optional)",
    )
    args = parser.parse_args()

    # Set environment variables if provided via CLI
    if args.openai_api_key:
        os.environ["OPENAI_API_KEY"] = args.openai_api_key
    if args.openrouter_api_key:
        os.environ["OPENROUTER_API_KEY"] = args.openrouter_api_key
    if args.model:
        os.environ["MODEL_NAME"] = args.model

    print("🤖 Research Agent - Investigative Journalism AI")
    print("📰 Capabilities: Web search, article extraction, NYT-style reporting")

    # Load configuration
    config = load_config()

    try:
        # Bindufy and start the agent server
        print("🚀 Starting Bindu Research Agent server...")
        print(f"🌐 Server will run on: {config.get('deployment', {}).get('url', 'http://127.0.0.1:3773')}")
        bindufy(config, handler)
    except KeyboardInterrupt:
        print("\n🛑 Research Agent stopped")
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup on exit
        asyncio.run(cleanup())


if __name__ == "__main__":
    main()
