from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List

app = FastAPI(title="Bindu Hub - Identity & Ledger Layer")

agents_registry: Dict[str, dict] = {}
ledger: Dict[str, float] = {}

class AgentRegistration(BaseModel):
    agent_id: str
    capabilities: List[str]
    endpoint_url: str

class Transaction(BaseModel):
    sender_id: str
    receiver_id: str
    amount: float

@app.post("/registry/register")
async def register_agent(agent: AgentRegistration):
    agents_registry[agent.agent_id] = agent.model_dump()
    # Give the buyer a budget. Sellers start at 0.
    ledger[agent.agent_id] = 100.0 if "buyer" in agent.capabilities else 0.0
    return {"status": "success", "message": f"{agent.agent_id} registered."}

@app.get("/registry/discover")
async def discover_agents(capability: str):
    matches = [info for info in agents_registry.values() if capability in info["capabilities"]]
    return {"available_agents": matches}

@app.post("/ledger/transfer")
async def transfer_funds(tx: Transaction):
    if tx.sender_id not in ledger or tx.receiver_id not in ledger:
        raise HTTPException(status_code=404, detail="Wallet not registered.")
    if ledger[tx.sender_id] < tx.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds.")
        
    ledger[tx.sender_id] -= tx.amount
    ledger[tx.receiver_id] += tx.amount
    return {"status": "success", "amount": tx.amount}