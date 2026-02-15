from fastapi import FastAPI
import httpx

app = FastAPI(title="Portfolio Manager Agent")
AGENT_ID = "agent_manager_buyer"

@app.on_event("startup")
async def register():
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/registry/register", json={
            "agent_id": AGENT_ID,
            "capabilities": ["buyer"],
            "endpoint_url": "http://localhost:8003"
        })

@app.get("/execute_research")
async def execute_research(asset: str = "bitcoin"):
    async with httpx.AsyncClient() as client:
        # 1. Discover Agents via Bindu Hub
        sentiment_discovery = await client.get("http://localhost:8000/registry/discover?capability=sentiment_analysis")
        quant_discovery = await client.get("http://localhost:8000/registry/discover?capability=quant_analysis")
        
        sentiment_url = sentiment_discovery.json()["available_agents"][0]["endpoint_url"]
        quant_url = quant_discovery.json()["available_agents"][0]["endpoint_url"]

        # 2. Query & Pay Agents
        sentiment_response = await client.post(f"{sentiment_url}/agent/sentiment/analyze", json={
            "asset": asset, "buyer_id": AGENT_ID
        })
        quant_response = await client.post(f"{quant_url}/agent/quant/process", json={
            "asset": asset, "buyer_id": AGENT_ID
        })

        # 3. Synthesize the final decision
        return {
            "decision": "BUY" if sentiment_response.json()["data"]["score"] > 0.7 else "HOLD",
            "sentiment_intel": sentiment_response.json(),
            "quant_intel": quant_response.json()
        }