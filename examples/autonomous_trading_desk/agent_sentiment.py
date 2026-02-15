from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx

app = FastAPI(title="Sentiment Agent")
AGENT_ID = "agent_sentiment_01"
PRICE = 5.0

class AnalyzeRequest(BaseModel):
    asset: str
    buyer_id: str

@app.on_event("startup")
async def register():
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/registry/register", json={
            "agent_id": AGENT_ID,
            "capabilities": ["sentiment_analysis"],
            "endpoint_url": "http://localhost:8001"
        })

@app.post("/agent/sentiment/analyze")
async def analyze_sentiment(request: AnalyzeRequest):
    # Verify payment via Bindu Hub before releasing data
    async with httpx.AsyncClient() as client:
        payment = await client.post("http://localhost:8000/ledger/transfer", json={
            "sender_id": request.buyer_id,
            "receiver_id": AGENT_ID,
            "amount": PRICE
        })
        if payment.status_code != 200:
            raise HTTPException(status_code=402, detail="Payment Required")

    # Generate the analysis
    target = request.asset.lower()
    if target in ["bitcoin", "btc"]:
        sentiment = {"score": 0.82, "summary": "Strong bullish momentum and positive funding rates."}
    elif target == "hyperliquid":
        sentiment = {"score": 0.75, "summary": "Growing DEX volume and high trader retention."}
    else:
        sentiment = {"score": 0.5, "summary": "Neutral market conditions."}

    return {"source": AGENT_ID, "data": sentiment}