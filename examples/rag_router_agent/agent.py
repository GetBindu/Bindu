import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat

from router import classify_intent, route_db
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
            "db_used": None,
            "docs_used": []
        }

    query = messages[-1]["content"].strip()

    if not query:
        return {
            "answer": "Empty query provided.",
            "intent": None,
            "db_used": None,
            "docs_used": []
        }

    # 🔍 Step 1: Intent classification
    intent = classify_intent(query)

    # 🧭 Step 2: Route to DB
    db_path = route_db(intent)

    # 📦 Step 3: Retrieve documents
    docs = retrieve_docs(db_path, query)

    # ⚠️ Handle no results
    if not docs:
        return {
            "answer": "No relevant information found in the database.",
            "intent": intent,
            "db_used": db_path,
            "docs_used": []
        }

    context = "\n".join(docs)

    # 🤖 Step 4: Generate response
    prompt = f"""
Context:
{context}

Question:
{query}

Answer clearly based only on the context above:
"""

    try:
        result = agent.run(prompt)
        answer = result.content if hasattr(result, "content") else str(result)
    except Exception:
        return {
            "answer": "Error generating response. Please try again.",
            "intent": intent,
            "db_used": db_path,
            "docs_used": docs,
        }

    return {
        "answer": answer.strip(),
        "intent": intent,
        "db_used": db_path,
        "docs_used": docs,
    }


# ⚙️ Bindu config
config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "rag_router_agent",
    "description": "RAG agent with intelligent database routing",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}


# 🚀 Start agent only when run directly
if __name__ == "__main__":
    bindufy(config, handler)