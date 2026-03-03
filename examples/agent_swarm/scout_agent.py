"""
Scout Agent — LangGraph ReAct web research agent.
Deployed as an independent Bindu microservice.
Runs autonomously on Redis schedule.
"""

import asyncio
import os
import operator
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from bindu.penguin.bindufy import bindufy

load_dotenv(override=True)

# ── LLM ───────────────────────────────────────────────────────────────────────
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3,
)

# ── Tools ─────────────────────────────────────────────────────────────────────
search = DuckDuckGoSearchRun()
tools = [search]
llm_with_tools = llm.bind_tools(tools)

# ── State ─────────────────────────────────────────────────────────────────────
class ScoutState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    iterations: int

# ── Nodes ─────────────────────────────────────────────────────────────────────
def scout_node(state: ScoutState) -> dict:
    """Core reasoning node — calls LLM with tools bound."""
    response = llm_with_tools.invoke(state["messages"])
    return {
        "messages": [response],
        "iterations": state["iterations"] + 1,
    }

def should_continue(state: ScoutState) -> str:
    """Stop if no tool calls remain or max iterations reached."""
    last = state["messages"][-1]
    if not getattr(last, "tool_calls", None) or state["iterations"] >= 5:
        return END
    return "tools"

# ── Graph ──────────────────────────────────────────────────────────────────────
tool_node = ToolNode(tools)

graph = StateGraph(ScoutState)
graph.add_node("scout", scout_node)
graph.add_node("tools", tool_node)
graph.set_entry_point("scout")
graph.add_conditional_edges("scout", should_continue)
graph.add_edge("tools", "scout")

scout_graph = graph.compile()

# ── Handler ───────────────────────────────────────────────────────────────────
def handler(messages: list[dict[str, str]]) -> str:
    """
    Bindu-compatible handler.
    Receives A2A messages, runs ReAct research loop, returns findings.
    """
    if not messages:
        return "No input received."

    topic = messages[-1].get("content", "")
    if not topic:
        return "Empty research topic."

    print(f"\n🔍 Scout Agent — researching: {topic}")

    try:
        result = scout_graph.invoke({
            "messages": [HumanMessage(content=(
                f"Research the following topic thoroughly using web search. "
                f"Find recent, specific, factual information.\n\nTopic: {topic}"
            ))],
            "iterations": 0,
        })

        final_message = result["messages"][-1]
        raw_content = final_message.content if hasattr(final_message, "content") else ""

        if isinstance(raw_content, list):
        # Extract text from content blocks
            findings = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            )
        elif isinstance(raw_content, str):
            findings = raw_content
        else:
            findings = str(raw_content)

        findings = findings.strip()
        if not findings:
            findings = "No findings returned."

        print(f"✅ Scout completed — {len(findings)} chars of findings")
        return findings

    except Exception as e:
        print(f"❌ Scout failed: {e}")
        return f"Research failed: {str(e)}"


# ── Autonomous scheduled research ──────────────────────────────────────────────
def run_autonomous_research(topic: str) -> str:
    """Called by Redis scheduler — runs one research cycle."""
    return handler([{"role": "user", "content": topic}])


# ── Bindu config ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import threading

    config = {
        "author": "nivasm2823@gmail.com",
        "name": "scout-agent",
        "description": "LangGraph ReAct web research agent. Searches and synthesizes recent information on any topic.",
        "capabilities": {"streaming": False},
        "deployment": {
            "url": "http://localhost:3781",
            "expose": True,
            "protocol_version": "1.0.0",
        },
        "storage": {"type": "memory"},
        "scheduler": {
            "type": "redis",
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379"),
        },
    }

    # Start autonomous research loop in background
    autonomous_enabled = os.getenv("SWARM_AUTONOMOUS_MODE", "false").lower() == "true"
    if autonomous_enabled:
        topic = os.getenv(
            "SWARM_RESEARCH_TOPIC",
            "latest developments in AI agents and multi-agent systems"
        )
        interval_hours = float(os.getenv("SWARM_RESEARCH_INTERVAL_HOURS", "6"))
        interval_seconds = interval_hours * 3600

        def autonomous_loop():
            import time
            print(f"\n🔁 Scout autonomous mode — topic: {topic}, interval: {interval_hours}h")
            while True:
                run_autonomous_research(topic)
                print(f"⏳ Next scout run in {interval_hours}h")
                time.sleep(interval_seconds)

        thread = threading.Thread(target=autonomous_loop, daemon=True)
        thread.start()

    bindufy(config=config, handler=handler)