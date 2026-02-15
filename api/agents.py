from fastapi import APIRouter
from bindu.schemas.agent import AgentCreate
from bindu.services.agent_registry import register_agent, list_agents

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/")
def create_agent(agent: AgentCreate):
    return register_agent(agent)

@router.get("/")
def get_agents():
    return list_agents()
