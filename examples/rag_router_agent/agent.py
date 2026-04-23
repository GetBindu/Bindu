import os
import logging

from agno.agent import Agent
from agno.models.openai import OpenAIChat

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

logger = logging.getLogger(__name__)

api_key = os.getenv("OPENROUTER_API_KEY")

# ✅ Safe agent init
agent = None
if api_key:
    agent = Agent(
        instructions="You are a helpful assistant that answers based only on the given context.",
        model=OpenAIChat(
            id="openai/gpt-4o-mini",
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
        ),
    )


def handler(messages: list[dict]):
    if not messages or "content" not in messages[-1]:
        return _error("Invalid input")

    query = messages[-1]["content"].strip()

    intent = classify_intent(query)
    if not intent:
        return _error("No intent found")

    source = select_source(intent, query)
    if not source:
        return _error("No source found")

    db_path = source["path"]

    payment = None
    payment_reason = "free_access"

    if source.get("type") == "premium":
        payment_reason = "premium_data_access"
        payment = call_skale_facilitator()

        if not payment or payment.get("status") not in ("success", "reachable"):
            return _base("Payment required but failed.", intent, db_path, [], payment, payment_reason)

    docs = retrieve_docs(db_path, query)

    if not docs:
        return _base("No relevant information found.", intent, db_path, [], payment, payment_reason)

    context = "\n".join(docs)

    agent_fn = route_agent(intent)

    try:
        agent_response = agent_fn(query, context)
    except Exception:
        logger.exception("Agent execution failed")
        agent_response = "Agent failed"

    # ✅ Safe LLM fallback
    if not agent:
        answer = agent_response
    else:
        try:
            result = agent.run(f"{query}\n{context}")
            answer = getattr(result, "content", str(result))
        except Exception:
            logger.exception("LLM failed")
            answer = agent_response

    return _base(answer.strip(), intent, db_path, docs, payment, payment_reason)


def _error(msg):
    return {
        "answer": msg,
        "intent": None,
        "agent_used": None,
        "db_used": None,
        "docs_used": [],
        "payment": None,
        "payment_reason": None,
    }


def _base(answer, intent, db_path, docs, payment, reason):
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # ✅ Normalize path (fix README mismatch)
    db_path_rel = os.path.relpath(db_path, base_dir)

    return {
        "answer": answer,
        "intent": intent,
        "agent_used": intent,
        "db_used": db_path_rel,
        "docs_used": docs,
        "payment": payment,
        "payment_reason": reason,
    }


config = {
    "author": os.getenv("BINDU_AUTHOR", "your.email@example.com"),
    "name": "rag_router_agent",
    "description": "Payment-aware RAG agent",
    "deployment": {
        "url": os.getenv("BINDU_DEPLOYMENT_URL", "http://localhost:3773"),
        "expose": True,
    },
    "skills": [],
}


if __name__ == "__main__":
    from bindu.penguin.bindufy import bindufy
    bindufy(config, handler)