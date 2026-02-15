from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import pandas as pd
import numpy as np

app = FastAPI(title="Quant Agent")
AGENT_ID = "agent_quant_01"
PRICE = 10.0

class QuantRequest(BaseModel):
    asset: str
    buyer_id: str

@app.on_event("startup")
async def register():
    async with httpx.AsyncClient() as client:
        await client.post("http://localhost:8000/registry/register", json={
            "agent_id": AGENT_ID,
            "capabilities": ["quant_analysis"],
            "endpoint_url": "http://localhost:8002"
        })

@app.post("/agent/quant/process")
async def process_data(request: QuantRequest):
    async with httpx.AsyncClient() as client:
        payment = await client.post("http://localhost:8000/ledger/transfer", json={
            "sender_id": request.buyer_id,
            "receiver_id": AGENT_ID,
            "amount": PRICE
        })
        if payment.status_code != 200:
            raise HTTPException(status_code=402, detail="Payment Required")

    # You can plug in your actual Bitcoin or Hyperliquid datasets here to analyze trader performance.
    # For this PR example, we generate a mock Pandas dataframe:
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30)
    df = pd.DataFrame({
        "price": np.random.normal(100, 5, 30).cumsum(),
        "volume": np.random.randint(1000, 5000, 30)
    }, index=dates)
    
    volatility = df["price"].pct_change().std() * np.sqrt(365)
    moving_average = df["price"].rolling(window=7).mean().iloc[-1]

    return {
        "source": AGENT_ID, 
        "data": {"volatility_annualized": volatility, "7d_ma": moving_average}
    }