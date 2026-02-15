from typing import Dict
from bindu.schemas.agent import AgentCreate

AGENT_REGISTRY: Dict[str, AgentCreate] = {}

def register_agent(agent: AgentCreate):
    AGENT_REGISTRY[agent.agent_id] = agent
    return agent

def list_agents():
    return list(AGENT_REGISTRY.values())
