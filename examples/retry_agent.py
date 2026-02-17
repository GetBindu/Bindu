"""
Retry Agent Example
===================

This example shows how to use Bindu's retry mechanism to make your agent
resilient against transient failures (network blips, timeouts, rate limits).

Without retry:  one failure = agent is dead
With retry:     agent quietly recovers and the caller never knows it failed

Run this file directly to see retry in action with a simulated flaky handler:
    python examples/retry_agent.py

To use retry in your real Bindu agent, simply add a "retry" block to your config.
"""

import logging
import random

from bindu.penguin.retry import RetryConfig, RetryExhaustedError, with_retry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)


# ---------------------------------------------------------------------------
# Simulate a flaky external AI service
# ---------------------------------------------------------------------------

_call_count = 0

def flaky_ai_handler(messages: list[dict]) -> list[dict]:
    """Simulates a real-world handler that sometimes fails.

    Fails on the first 2 calls, succeeds on the 3rd.
    In production this could be: a timeout from an LLM API,
    a 429 rate-limit response, or a temporary network error.
    """
    global _call_count
    _call_count += 1

    print(f"\n  → Handler called (attempt #{_call_count})")

    if _call_count < 3:
        raise ConnectionError(f"Simulated network failure on attempt #{_call_count}")

    user_message = messages[-1]["content"] if messages else "hello"
    return [{"role": "assistant", "content": f"Echo: {user_message}"}]


# ---------------------------------------------------------------------------
# Demo 1: Without retry — it just crashes
# ---------------------------------------------------------------------------

def demo_without_retry():
    print("\n" + "=" * 55)
    print("DEMO 1: Without retry (handler will crash)")
    print("=" * 55)

    global _call_count
    _call_count = 0

    try:
        result = flaky_ai_handler([{"role": "user", "content": "Hello Bindu!"}])
        print(f"  ✅ Result: {result}")
    except ConnectionError as e:
        print(f"  ❌ CRASHED: {e}")
        print("  Agent is dead. User gets an error.")


# ---------------------------------------------------------------------------
# Demo 2: With retry — recovers silently
# ---------------------------------------------------------------------------

def demo_with_retry():
    print("\n" + "=" * 55)
    print("DEMO 2: With retry (handler will recover)")
    print("=" * 55)

    global _call_count
    _call_count = 0

    retry_config = RetryConfig(
        enabled=True,
        max_attempts=3,
        backoff_seconds=0.5,      # Wait 0.5s between retries
        backoff_multiplier=2.0,   # Then 1.0s, then 2.0s...
        max_backoff_seconds=10.0,
    )

    safe_handler = with_retry(flaky_ai_handler, retry_config)

    try:
        result = safe_handler([{"role": "user", "content": "Hello Bindu!"}])
        print(f"\n  ✅ SUCCESS: {result}")
        print("  User never knew about the failures!")
    except RetryExhaustedError as e:
        print(f"  ❌ All retries failed: {e}")


# ---------------------------------------------------------------------------
# Demo 3: What your real Bindu agent config looks like
# ---------------------------------------------------------------------------

def show_real_agent_config():
    print("\n" + "=" * 55)
    print("DEMO 3: Real Bindu agent config with retry")
    print("=" * 55)

    config = {
        "author": "your.email@example.com",
        "name": "resilient_research_agent",
        "description": "A research agent that never gives up.",
        "deployment": {"url": "http://localhost:3773", "expose": True},
        "skills": ["skills/question-answering"],

        # ✅ Just add this block to any Bindu agent for automatic retry
        "retry": {
            "enabled": True,
            "max_attempts": 3,
            "backoff_seconds": 1.0,
            "backoff_multiplier": 2.0,
            "max_backoff_seconds": 30.0,
        },
    }

    print("\n  Your agent config:")
    import json
    print(json.dumps(config, indent=4))
    print("\n  Bindu reads the 'retry' block and automatically wraps your handler.")
    print("  No code changes needed in your handler function!")


# ---------------------------------------------------------------------------
# Run all demos
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n🌻 Bindu Retry Mechanism Demo\n")
    print("Bindu agents can now recover from transient failures automatically.")
    print("Just add a 'retry' block to your config — that's it.")

    demo_without_retry()
    demo_with_retry()
    show_real_agent_config()

    print("\n" + "=" * 55)
    print("✅ Retry mechanism working correctly!")
    print("=" * 55)
    print("\nPeace ☮️ + Plants 🌱")
