# Data Extraction Negotiator Agent This agent was built as a submission for the GetBindu Software Engineering Internship Assessment. 
Instead of building a standard wrapper agent, I implemented a **Task-First Negotiator** that strictly follows the Bindu **Agentic 
Protocol 2 (AP2)**. ### What makes this a "Surprise": 1. **Dynamic Negotiation:** Implements the `POST /agent/negotiation` endpoint. 2. 
**Protocol Adherence:** It dynamically parses the orchestrator's request, extracting the specific `weights` and `min_score` thresholds. 
3. **Internal Scoring:** It calculates its own confidence score using the exact formula `(skill*w + io*w + perf*w + load*w + cost*w)` 
before accepting a task. 4. **Automated Testing:** Includes a `pytest` suite to verify both the acceptance of matching tasks and the 
strict rejection of unrelated tasks, contributing to the repo's 80% coverage goal. ### How to Run & Test uv run uvicorn main:app --host 
0.0.0.0 --port 3773
uv run pytest test_main.py


