"""Notte Browser Agent (Bindu example).

Wraps the Notte SDK's built-in Agent + Session as a Bindu microservice.
Notte provides the browser runtime (cloud Chromium, stealth, captcha solving,
proxies, Vault-backed auth) and the agent loop that turns a natural-language
task into structured Pydantic output. `bindufy(...)` exposes that as a
Bindu-native agent with DID identity, A2A protocol, and skill routing.

Unlike most Bindu examples, there is no separate "LLM + tools" layer here —
Notte IS the agent. The handler simply forwards the user message to
`client.Agent(...).run(task=...)`.

Usage:
    python notte_browser_agent.py

Environment:
    Requires NOTTE_API_KEY in .env (https://console.notte.cc to obtain one).

Docs:
    - Notte SDK:            https://github.com/nottelabs/notte
    - Notte docs:           https://docs.notte.cc
    - Agent Skill (Claude): https://github.com/nottelabs/agent-skill-notte
"""

import os

from dotenv import load_dotenv

load_dotenv()

from bindu.penguin.bindufy import bindufy
from notte_sdk import NotteClient

# A single, long-lived Notte client. Session lifetime is scoped per request
# inside the handler so every A2A call gets an isolated browser context.
client = NotteClient()

# Sensible default model. Escalate to anthropic/claude-sonnet-4-5 or
# openai/gpt-4.1 for harder multi-step flows via NOTTE_REASONING_MODEL.
REASONING_MODEL = os.getenv("NOTTE_REASONING_MODEL", "gemini/gemini-2.5-flash")
MAX_STEPS = int(os.getenv("NOTTE_MAX_STEPS", "15"))
SOLVE_CAPTCHAS = os.getenv("NOTTE_SOLVE_CAPTCHAS", "false").lower() == "true"
USE_PROXIES = os.getenv("NOTTE_USE_PROXIES", "false").lower() == "true"

# Bindu agent configuration
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "notte_browser_agent",
    "description": (
        "Real-browser web automation agent powered by Notte. Navigates JS-rendered "
        "pages, fills forms, handles auth, solves captchas, and returns Pydantic-"
        "validated structured output."
    ),
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "skills": ["skills/notte-browser-skill"],
}


def handler(messages: list[dict[str, str]]) -> str:
    """Run the latest user message as a Notte browser task.

    Args:
        messages: A2A message history; we use the latest user turn as the task.

    Returns:
        The agent's final answer as a string (JSON if the caller asked for
        structured output, free text otherwise).
    """
    if not messages:
        return (
            "Please provide a browser task. Example: 'Go to news.ycombinator.com "
            "and return the top 5 posts as JSON with title, url, and points.'"
        )

    latest_user = next(
        (
            m
            for m in reversed(messages)
            if isinstance(m, dict) and m.get("role") == "user"
        ),
        None,
    )
    if latest_user is None:
        return "No user message found — please send a task as a user-role message."
    task = latest_user.get("content", "")
    if not isinstance(task, str) or not task.strip():
        return "Empty task — please describe the browser action you want."

    with client.Session(
        solve_captchas=SOLVE_CAPTCHAS,
        proxies=USE_PROXIES,
    ) as session:
        agent = client.Agent(
            session=session,
            reasoning_model=REASONING_MODEL,
            max_steps=MAX_STEPS,
        )
        response = agent.run(task=task)

    answer = getattr(response, "answer", None)
    if answer is None:
        return "Notte agent returned no answer — try raising NOTTE_MAX_STEPS or a stronger NOTTE_REASONING_MODEL."
    return answer


if __name__ == "__main__":
    bindufy(config, handler)
