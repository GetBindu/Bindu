from database.db import get_agents
from core.negotiation_engine import agent_bid, choose_best_agent
from core.collaboration_engine import collaboration_pipeline

from agents.agent_executor import research_agent
from agents.agent_executor import finance_agent
from agents.agent_executor import summary_agent


def route_task(task_description):

    agents = get_agents()

    pipeline = collaboration_pipeline(task_description)

    execution_bids = []

    for agent_id in pipeline:

        if agent_id in agents:

            reputation = agents[agent_id]["reputation"]

            bid = agent_bid(agent_id, reputation)

            execution_bids.append(bid)

    best_agent = choose_best_agent(execution_bids)

    result = None

    if "research_agent" in pipeline:
        result = research_agent(task_description)

    if "finance_agent" in pipeline:
        result = finance_agent(result)

    if "summary_agent" in pipeline:
        result = summary_agent(result)

    return {
        "pipeline": pipeline,
        "selected_agent": best_agent,
        "result": result
    }