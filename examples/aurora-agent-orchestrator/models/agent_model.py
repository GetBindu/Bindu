from pydantic import BaseModel

class Agent(BaseModel):
    agent_id: str
    capability: str
    reputation: float = 5.0