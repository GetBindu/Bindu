"""
PR Review Agent Example

This agent demonstrates how Bindu can be used to build
developer-facing tooling agents.

It analyzes a git diff and returns structured review comments
for common issues like TODOs and hardcoded secrets.
"""

from bindu.penguin.bindufy import bindufy


def handler(messages):
    """
    Analyze a git diff and return structured review feedback.

    Args:
        messages: List of message dictionaries containing conversation history.
                  The latest message is expected to contain a git diff.

    Returns:
        List containing a single assistant message with structured review output.
    """

    diff = messages[-1]["content"]
    issues = []

    # Simple checks (intentionally minimal)
    if "TODO" in diff:
        issues.append({
            "type": "todo",
            "message": "TODO found in code. Consider resolving before merge."
        })

    if "password =" in diff or "API_KEY" in diff:
        issues.append({
            "type": "security",
            "message": "Hardcoded secret detected. Use environment variables instead."
        })

    if not issues:
        issues.append({
            "type": "info",
            "message": "No obvious issues found in the diff."
        })

    return [{
        "role": "assistant",
        "content": {
            "review_comments": issues
        }
    }]


config = {
    "author": "mayur@example.com",
    "name": "pr_review_agent",
    "description": "A minimal agent that reviews git diffs and flags common issues.",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True
    },
    "skills": []
}


bindufy(config, handler)
