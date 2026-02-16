from bindu.penguin.bindufy import bindufy
from graph import build_graph
from schemas import AgentResponse

graph = build_graph()

def handler(messages):
    query = messages[0]["content"]

    result = graph.invoke({
        "topic": query,
    "plan":  None,
    "sections": [],  # reducer concatenates worker outputs
    "final": ""

    })

    return AgentResponse(
        answer=result["final"],
        reasoning="Generated via LangGraph blog writter agent"
    ).dict()

config = {
    "author": "amritanshu9973@gmail.com",
    "name": "langgraph_blog_writing_agent",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["*"],
    }
}

bindufy(config, handler)
