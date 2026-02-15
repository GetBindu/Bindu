from pydantic import BaseModel
from typing import List

class AgentCreate(BaseModel):
    agent_id: str
    name: str
    capabilities: List[str]

class AgentResponse(AgentCreate):
    pass
