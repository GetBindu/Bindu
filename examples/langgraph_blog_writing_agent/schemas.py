from pydantic import BaseModel
from typing import Optional

class AgentResponse(BaseModel):
    answer: Optional[str]
    reasoning: Optional[str] = None
