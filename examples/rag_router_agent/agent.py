import os
from bindu.penguin.bindufy import bindufy
from agno.agent import Agent
from agno.models.openai import OpenAIChat




from skale_payment import call_skale_facilitator
from router import classify_intent, route_db, route_agent
from retriever import retrieve_docs





# 🔐 Validate API key at startup
api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENROUTER_API_KEY is not set. See examples/rag_router_agent/README.md."
    )


# 🤖 LLM setup (OpenRouter)
agent = Agent(
    instructions="You are a helpful assistant that answers based only on the given context.",
    model=OpenAIChat(
        id="openai/gpt-4o-mini",
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1"
    ),
)


def handler(messages: list[dict]):
    # 🧠 Input validation
    if (
        not isinstance(messages, list)
        or not messages
        or not isinstance(messages[-1], dict)
        or "content" not in messages[-1]
        or not isinstance(messages[-1]["content"], str)
    ):
        return _error_response("Invalid input format.")

    query = messages[-1]["content"].strip()

    if not query:
        return _error_response("Empty query provided.")

    # 🔍 Step 1: Intent classification
    intent = classify_intent(query)

    if intent is None:
        return _error_response("No relevant domain found for this query.")

    # 📦 Step 2: Retrieve context
    db_path = route_db(intent)
    docs = retrieve_docs(db_path, query)

    if not docs:
        return _base_response(
            answer="No relevant information found.",
            intent=intent,
            db_path=db_path,
            docs=[]
        )

    context = "\n".join(docs)

    # 🔀 Step 3: Route to domain agent
    agent_fn = route_agent(intent)

    if agent_fn is None:
        return _base_response(
            answer="No agent available for this intent.",
            intent=intent,
            db_path=db_path,
            docs=docs
        )

    agent_response = agent_fn(query, context)

    # 🤖 Step 4: LLM refinement
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
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}")
        answer = "Error generating response. Please try again."

    # 💳 Step 5: SKALE facilitator call
    payment_result = call_skale_facilitator()

    return _base_response(
        answer=answer.strip(),
        intent=intent,
        db_path=db_path,
        docs=docs,
        payment=payment_result
    )


# 🧱 Helper responses (cleaner + reusable)
def _error_response(message: str):
    return {
        "answer": message,
        "intent": None,
        "agent_used": None,
        "db_used": None,
        "docs_used": [],
        "payment": None
    }


def _base_response(answer, intent, db_path, docs, payment=None):
    return {
        "answer": answer,
        "intent": intent,
        "agent_used": intent,
        "db_used": db_path,
        "docs_used": docs,
        "payment": payment
    }


# ⚙️ Bindu config
config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "rag_router_agent",
    "description": "RAG agent with intelligent routing + multi-agent delegation + SKALE facilitator integration",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}


# 🚀 Run agent
if __name__ == "__main__":
    bindufy(config, handler)