from pydantic import BaseModel

class Task(BaseModel):
    task_id: str
    description: str