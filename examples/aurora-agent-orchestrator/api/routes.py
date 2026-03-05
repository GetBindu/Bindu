from fastapi import APIRouter
from models.agent_model import Agent
from models.task_model import Task
from database.db import register_agent, store_task, get_agents
from core.task_router import route_task

router = APIRouter()


@router.post("/register_agent")
def register(agent: Agent):

    register_agent(agent.agent_id, agent.capability, agent.reputation)

    return {
        "message": "Agent registered",
        "agent_id": agent.agent_id
    }


@router.post("/create_task")
def create(task: Task):

    store_task(task.task_id, task.description)

    result = route_task(task.description)

    return result


@router.get("/agents")
def list_agents():

    return get_agents()