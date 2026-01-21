"""
Bug Explainer Agent

This file demonstrates a simple session-based agent that explains Python errors
using an LLM.

Design:
- Core reasoning logic lives in `skills/bug_explainer.py`
- This agent handles interaction, looping, and exit control

Why this separation:
- Keeps the explainer stateless and reusable
- Allows the agent to manage UX without mixing concerns

How to use:
- Run this file
- Paste a Python error and press Enter twice
- Type 'exit' or 'e' to quit the session
"""
from skills.bug_Explainer import explain_error


def run_agent():
    print("🤖 Bug Explainer Agent (Session Mode)")
    print("Paste a Python error and press Enter twice.")
    print("Type 'exit' or 'e' to quit.\n")

    while True:
        print("Paste Python error or Type 'exit' or 'e' to quit.\n")
        lines = []

        while True:
            line = input()
            if line.strip() == "":
                break

            if line.lower() in ("exit", "e", "quit"):
                print("👋 Agent stopped")
                return

            lines.append(line)

        error_text = "\n".join(lines).strip()

        if not error_text:
            continue

        print("\n--- Agent Output ---\n")
        explanation = explain_error(error_text)
        print(explanation)
        print("\n--------------------\n")


if __name__ == "__main__":
    run_agent()