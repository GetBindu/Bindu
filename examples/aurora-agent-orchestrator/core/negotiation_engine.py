import random


def agent_bid(agent_id, reputation):

    price = round(random.uniform(0.01, 0.10), 3)
    latency = round(random.uniform(1, 5), 2)

    score = round((price * 0.4) + (latency * 0.3) - (reputation * 0.3), 4)

    return {
        "agent": agent_id,
        "price": price,
        "latency": latency,
        "reputation": reputation,
        "score": score
    }


def choose_best_agent(bids):

    if not bids:
        return {
            "agent": "no_available_agent",
            "price": 0,
            "latency": 0,
            "reputation": 0,
            "score": 0
        }

    bids.sort(key=lambda x: x["score"])

    return bids[0]