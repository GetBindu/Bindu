import time
from examples.multi_agent_research.agents.search_agent import search_agent
from examples.multi_agent_research.agents.summary_agent import summary_agent
from examples.multi_agent_research.agents.verifier_agent import verifier_agent
from examples.multi_agent_research.utils.llm import call_llm


def run_pipeline(query: str):
    # ------------------ SEARCH ------------------
    print("\n[SEARCH AGENT]")
    start = time.time()
    search_result = search_agent(query)
    print(f"[TIME] Search took {time.time() - start:.2f}s\n")

    # ------------------ SUMMARY ------------------
    print("[SUMMARY AGENT]")
    start = time.time()
    summary = summary_agent(search_result)
    print(f"[TIME] Summary took {time.time() - start:.2f}s\n")

    # ------------------ VERIFY ------------------
    print("[VERIFIER AGENT]")
    start = time.time()
    verification = verifier_agent(summary)
    print(f"[TIME] Verification took {time.time() - start:.2f}s\n")

    
    if "STATUS: VALID" not in verification:
        print("\n[COLLABORATION] Improving summary based on feedback...\n")

        improve_prompt = f"""
You are an advanced AI system.

Your task is to improve a summary using feedback from another agent.

Original Summary:
{summary}

Feedback from Verifier:
{verification}

Instructions:
- Fix inaccuracies
- Add missing points
- Remove hallucinations
- Keep it concise (5 bullet points only)

Return only improved summary.
"""

        start = time.time()
        improved_summary = call_llm(improve_prompt)
        print(f"[TIME] Improvement took {time.time() - start:.2f}s\n")

        # Re-verify improved summary
        print("[RE-VERIFICATION]")
        start = time.time()
        new_verification = verifier_agent(improved_summary)
        print(f"[TIME] Re-verification took {time.time() - start:.2f}s\n")

        summary = improved_summary
        verification = new_verification

    return search_result, summary, verification