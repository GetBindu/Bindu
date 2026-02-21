from examples.multi_agent_research.utils.llm import call_llm


def verifier_agent(summary: str) -> str:
    prompt = f"""
You are a strict evaluator.

Check the summary based on:
1. Accuracy
2. Completeness
3. Hallucination

Return ONLY in this format:

STATUS: VALID or INVALID

FEEDBACK:
- point 1
- point 2
- point 3

Summary:
{summary}
"""
    return call_llm(prompt)