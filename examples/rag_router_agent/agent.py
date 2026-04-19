import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from router import classify_intent, route_db, route_agent
from retriever import retrieve_docs


# 🔑 LLM setup (OpenRouter)
agent = Agent(
    instructions="You are a helpful assistant that answers based only on the given context.",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    ),
)


def handler(messages: list[dict]):
    # 🧠 Robust input validation
    if (
        not isinstance(messages, list)
        or len(messages) == 0
        or not isinstance(messages[-1], dict)
        or "content" not in messages[-1]
        or not isinstance(messages[-1]["content"], str)
    ):
        return {
            "answer": "Invalid input format.",
            "intent": None,
            "agent_used": None,
            "db_used": None,
            "docs_used": []
        }

    query = messages[-1]["content"].strip()

    if not query:
        return {
            "answer": "Empty query provided.",
            "intent": None,
            "agent_used": None,
            "db_used": None,
            "docs_used": []
        }

    # 🔍 Step 1: Intent classification
    intent = classify_intent(query)

    # 📦 Step 2: Retrieve context
    db_path = route_db(intent)
    docs = retrieve_docs(db_path, query)

    if not docs:
        return {
            "answer": "No relevant information found.",
            "intent": intent,
            "agent_used": intent,
            "db_used": db_path,
            "docs_used": []
        }

    context = "\n".join(docs)

    # 🔀 Step 3: Route to domain agent (A2A)
    agent_fn = route_agent(intent)
    agent_response = agent_fn(query, context)

    # 🤖 Step 4: LLM refines final answer
    final_prompt = f"""
User Query:
{query}

Agent Output:
{agent_response}

Provide a clear and final answer based only on the above.
"""

    try:
        result = agent.run(final_prompt)
        answer = result.content if hasattr(result, "content") else str(result)
    except Exception:
        answer = "Error generating response."

    return {
        "answer": answer.strip(),
        "intent": intent,
        "agent_used": intent,
        "db_used": db_path,
        "docs_used": docs,
    }


# ⚙️ Bindu config
config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "rag_router_agent",
    "description": "RAG agent with intelligent routing and multi-agent delegation",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}


# 🚀 Run agent
if __name__ == "__main__":
    bindufy(config, handler)