import os

if __name__ == "__main__":
    from bindu.penguin.bindufy import bindufy
    bindufy(config, handler)
from agno.agent import Agent
from agno.models.openai import OpenAIChat

# 🔁 Robust imports (module + script)
try:
    from .skale_payment import call_skale_facilitator
    from .router import classify_intent, route_agent
    from .retriever import retrieve_docs
    from .source_router import select_source
except ImportError:
    from skale_payment import call_skale_facilitator
    from router import classify_intent, route_agent
    from retriever import retrieve_docs
    from source_router import select_source


# 🔐 Safe API key handling
api_key = os.getenv("OPENROUTER_API_KEY")

if not api_key:
    print("[WARN] OPENROUTER_API_KEY not set — running in fallback mode")

# 🤖 LLM setup
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

    # 🔀 Step 2: Source selection (payment-aware)
    source = select_source(intent, query)

    if not source:
        return _error_response("No data source available for this query.")

    db_path = source["path"]

    # 💳 Step 3: Payment decision
    payment_result = None
    payment_reason = "free_access"

    if source.get("type") == "premium":
        payment_reason = "premium_data_access"
        payment_result = call_skale_facilitator()

        if payment_result.get("status") not in ["success", "reachable"]:
            return _base_response(
                answer="Payment required but failed.",
                intent=intent,
                db_path=db_path,
                docs=[],
                payment=payment_result,
                payment_reason=payment_reason,
            )

    # 📦 Step 4: Retrieve docs
    docs = retrieve_docs(db_path, query)

    if not docs:
        return _base_response(
            answer="No relevant information found.",
            intent=intent,
            db_path=db_path,
            docs=[],
            payment=payment_result,
            payment_reason=payment_reason,
        )

    context = "\n".join(docs)

    # 🔀 Step 5: Route to domain agent
    agent_fn = route_agent(intent)

    if agent_fn is None:
        return _base_response(
            answer="No agent available for this intent.",
            intent=intent,
            db_path=db_path,
            docs=docs,
            payment=payment_result,
            payment_reason=payment_reason,
        )

    # 🧠 Step 6: Agent execution
    try:
        agent_response = agent_fn(query, context)
    except Exception as e:
        print(f"[ERROR] Agent execution failed: {e}")
        agent_response = "Unable to process request via domain agent."

    # 🤖 Step 7: LLM refinement (safe fallback)
    if not api_key:
        answer = agent_response
    else:
        try:
            final_prompt = f"""
User Query:
{query}

Agent Output:
{agent_response}

Provide a clear and final answer based only on the above.
"""
            result = agent.run(final_prompt)
            content = getattr(result, "content", None)

            if isinstance(content, str) and content.strip():
                answer = content
            else:
                answer = str(result) if result is not None else agent_response

        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}")
            answer = agent_response

    # 🛡️ Ensure answer is string
    if not isinstance(answer, str):
        answer = str(answer) if answer is not None else ""

    return _base_response(
        answer=answer.strip(),
        intent=intent,
        db_path=db_path,
        docs=docs,
        payment=payment_result,
        payment_reason=payment_reason,
    )


# 🧱 Helper functions

def _error_response(message: str):
    return {
        "answer": message,
        "intent": None,
        "agent_used": None,
        "db_used": None,
        "docs_used": [],
        "payment": None,
        "payment_reason": None,
    }


def _base_response(answer, intent, db_path, docs, payment=None, payment_reason=None):
    return {
        "answer": answer,
        "intent": intent,
        "agent_used": intent,
        "db_used": db_path,
        "docs_used": docs,
        "payment": payment,
        "payment_reason": payment_reason,
    }


# ⚙️ Bindu config
config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "rag_router_agent",
    "description": "RAG agent with payment-aware routing and SKALE integration",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": []
}


# 🚀 Run agent
if __name__ == "__main__":
    bindufy(config, handler)