"""
Web Search Agent — Bindu Example
---------------------------------------
A research assistant agent built with Bindu.
Uses DuckDuckGo to search the web and OpenAI tool calling
to answer questions with real-time information.

Usage:
    python examples/beginner/langchain_search_agent.py

UI available at: http://localhost:3776/docs
"""

import json

import openai
from duckduckgo_search import DDGS

from bindu.penguin.bindufy import bindufy

# ------------------------------------------------------------------
# 1. Simple DuckDuckGo search function
# ------------------------------------------------------------------
def search_web(query: str, max_results: int = 3) -> str:
    """Search the web using DuckDuckGo and return results as text."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "No results found."
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. {r['title']}\n   {r['body']}\n   Source: {r['href']}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Search failed: {str(e)}"


# ------------------------------------------------------------------
# 2. Tool definition for OpenAI function calling
# ------------------------------------------------------------------
tools = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for current information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    }
                },
                "required": ["query"],
            },
        },
    }
]


# ------------------------------------------------------------------
# 3. Agent logic — ReAct loop with tool calling
# ------------------------------------------------------------------
def run_agent(user_message: str) -> str:
    """
    Run the search agent using OpenAI tool calling (ReAct pattern).
    The agent decides when to search and when to respond directly.
    """
    client = openai.OpenAI(
        base_url="https://openrouter.ai/api/v1",
    )

    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful research assistant. "
                "Use the search_web tool to find current, accurate information "
                "before answering questions. Always cite your sources."
            ),
        },
        {"role": "user", "content": user_message},
    ]

    # ReAct loop — keep going until agent gives final answer
    for _ in range(5):  # max 5 iterations
        response = client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        message = response.choices[0].message

        # If no tool call — we have the final answer
        if not message.tool_calls:
            return message.content or "I could not find an answer."

        # Add assistant message to history
        messages.append(message)

        # Execute each tool call
        for tool_call in message.tool_calls:
            if tool_call.function.name == "search_web":
                args = json.loads(tool_call.function.arguments)
                search_result = search_web(args["query"])

                # Add tool result back to conversation
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": search_result,
                })

    return "I reached the maximum number of search iterations. Please try a more specific question."


# ------------------------------------------------------------------
# 4. Handler function for Bindu
# ------------------------------------------------------------------
def handler(messages: list[dict]) -> list[dict]:
    """
    Process incoming A2A messages through the search agent.
    Bindu passes conversation history as a list of {role, content} dicts.
    """
    # Get the latest user message
    user_message = next(
        (m["content"] for m in reversed(messages) if m["role"] == "user"),
        "",
    )

    if not user_message:
        answer = "Please ask me a question and I'll search for the answer!"
    else:
        answer = run_agent(user_message)

    return [{"role": "assistant", "content": answer}]


# ------------------------------------------------------------------
# 5. Configuration and start
# ------------------------------------------------------------------
config = {
    "author": "your.email@example.com",
    "name": "web_search_agent",
    "description": "A research assistant that searches the web and answers questions with real-time information.",
    "deployment": {
        "url": "http://localhost:3776",
        "expose": True,
    },
    "skills": ["skills/question-answering"],
}

bindufy(config, handler)
