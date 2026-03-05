import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI

# initialize OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

class Query(BaseModel):
    question: str


def web_search(query):
    """
    Simple web search using DuckDuckGo instant answer API
    """
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json"
    }

    response = requests.get(url, params=params)
    data = response.json()

    results = []

    if "RelatedTopics" in data:
        for topic in data["RelatedTopics"][:5]:
            if "Text" in topic:
                results.append(topic["Text"])

    return results


def summarize(query, search_results):
    summary = "Research Results:\n\n"

    for i, result in enumerate(search_results, 1):
        summary += f"{i}. {result}\n"

    return summary

@app.post("/research")
def research(query: Query):
    results = web_search(query.question)

    summary = summarize(query.question, results)

    return {
        "question": query.question,
        "sources": results,
        "summary": summary
    }


@app.get("/")
def home():
    return {"message": "Research Agent is running"}