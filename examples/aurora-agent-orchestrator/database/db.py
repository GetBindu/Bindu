agents_store = {}
tasks_store = {}

def register_agent(agent_id, capability, reputation=5.0):
    agents_store[agent_id] = {
        "capability": capability,
        "reputation": reputation
    }

def get_agents():
    return agents_store

def store_task(task_id, task_data):
    tasks_store[task_id] = task_data

def get_tasks():
    return tasks_store