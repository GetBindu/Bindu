import uvicorn
from fastapi import FastAPI, Request
from agno.agent import Agent
from agno.models.openai import OpenAIChat

app = FastAPI(
    title="Data Extraction Negotiator Agent",
    description="An agent that negotiates to perform web scraping and data extraction tasks."
)

# 1. The Core Agent (Focused on Data Extraction & Scraping)
agent = Agent(
    name="DataExtractor",
    instructions="You are an expert at extracting structured data from unstructured text, web scrapes, and documents.",
    model=OpenAIChat(id="gpt-4o"),
)


# 2. The Negotiation Endpoint (Strictly matching the GetBindu API Docs)
@app.post("/agent/negotiation")
async def negotiate(request: Request):
    data = await request.json()

    # 1. Parse the full request
    task_summary = data.get("task_summary", "").lower()
    task_details = data.get("task_details", "").lower()
    combined_task_text = task_summary + " " + task_details

    # 2. Extract dynamic weights (with fallbacks if the orchestrator doesn't send them)
    weights = data.get("weights", {})
    w_skill = weights.get("skill_match", 0.6)
    w_io = weights.get("io_compatibility", 0.2)
    w_perf = weights.get("performance", 0.1)
    w_load = weights.get("load", 0.05)
    w_cost = weights.get("cost", 0.05)

    min_score_required = data.get("min_score", 0.5)

    # 3. Evaluate skills against both summary and details
    keywords = ["extract", "scrape", "data", "table", "structured", "parse", "pdf"]
    if any(word in combined_task_text for word in keywords):
        skill_match_score = 0.92
    else:
        skill_match_score = 0.15

    # 4. Agent's internal subscores
    io_compatibility = 1.0  # We handle PDF to JSON well
    performance = 0.85
    load = 0.90
    cost = 1.0

    # 5. Calculate final dynamic score based on Orchestrator's weights
    final_score = (
            (skill_match_score * w_skill) +
            (io_compatibility * w_io) +
            (performance * w_perf) +
            (load * w_load) +
            (cost * w_cost)
    )

    # Accept only if our calculated score beats the orchestrator's minimum
    accepted = final_score >= min_score_required

    return {
        "accepted": accepted,
        "score": round(final_score, 2),
        "confidence": 0.95 if accepted else 0.10,
        "skill_matches": [
            {
                "skill_id": "data-extraction-v1",
                "skill_name": "Data Extraction & Scraping",
                "score": skill_match_score,
                "reasons": [
                    "keyword match threshold met",
                    "tags: extraction, parsing, scraping, pdf",
                    "capabilities: text_extraction, table_extraction"
                ]
            }
        ],
        "matched_tags": ["extraction", "parsing", "scraping", "pdf"],
        "matched_capabilities": ["text_extraction", "table_extraction"],
        "latency_estimate_ms": 2000,
        "queue_depth": 0,
        "subscores": {
            "skill_match": skill_match_score,
            "io_compatibility": io_compatibility,
            "performance": performance,
            "load": load,
            "cost": cost
        }
    }

# 3. The Execution Endpoint (Standard A2A Protocol)
@app.post("/agent/execute")
async def execute_task(request: Request):
    """The endpoint called if the orchestrator selects this agent."""
    data = await request.json()
    prompt = data.get("prompt", "")

    # Run the Agno agent
    response = agent.run(input=prompt)

    return {
        "status": "success",
        "result": response.content
    }


if __name__ == "__main__":
    print("Starting Data Extraction Negotiator Agent on port 3773...")
    uvicorn.run(app, host="0.0.0.0", port=3773)