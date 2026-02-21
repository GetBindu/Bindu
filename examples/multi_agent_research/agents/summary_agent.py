from examples.multi_agent_research.utils.llm import call_llm


def summary_agent(text: str) -> str:
    prompt = f"""
Summarize the following into EXACTLY 5 bullet points.

Rules:
- Only bullet points
- No extra text
- Focus on key insights

{text}
"""
    return call_llm(prompt)