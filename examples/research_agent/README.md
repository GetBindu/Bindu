# Research Agent

This example demonstrates an AI research agent built using FastAPI.

The agent:
- Accepts a research question
- Searches the web
- Returns structured research results

## Endpoint

POST /research

Example Request

{
 "question": "What is quantum computing?"
}

## Response

{
 "question": "...",
 "sources": [...],
 "summary": "Research results..."
}

## Run Locally

pip install -r requirements.txt

uvicorn research_agent:app --reload