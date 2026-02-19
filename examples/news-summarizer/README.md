# News Summarizer Agent 🌻

A Bindu agent that searches and summarizes latest news on **any topic**
using local Ollama

## What Makes This Different?

Unlike the existing `summarizer` agent which summarizes text YOU provide,
this agent **actively searches the web** for latest news on any topic
and returns structured summaries with sentiment analysis.

## Features

- Real-time web search via DuckDuckGo
- Local LLM via Ollama (free, private, no data sent anywhere)
- Structured output: headlines + summaries + sentiment
- Works for any topic: cricket, tech, finance, politics

## Prerequisites

- Python 3.12+
- [Ollama](https://ollama.ai) running locally with llama3.2 model
- uv package manager

## Quick Start

### 1. Install Ollama and pull the model
```bash
ollama pull llama3.2
```

### 2. Set up environment
```bash
cp .env.example .env
```

### 3. Run the agent
```bash
# From Bindu root directory
python examples/news-summarizer/news_agent.py
```

### 4. Test it
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Give me latest cricket news"}],
        "kind": "message",
        "messageId": "550e8400-e29b-41d4-a716-446655440001",
        "contextId": "550e8400-e29b-41d4-a716-446655440002",
        "taskId": "550e8400-e29b-41d4-a716-446655440003"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

Then fetch the result:
```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/get",
    "params": {
      "taskId": "550e8400-e29b-41d4-a716-446655440003"
    },
    "id": "550e8400-e29b-41d4-a716-446655440000"
  }'
```

## Example Output
```
Top 3 Headlines:
1. Australia's T20 World Cup Failure Could Affect Olympic Cricket Bid
2. Former Cricket Captains Urge Pakistan to Improve Imran Khan's Prison Conditions
3. T20 World Cup: How to Watch Afghanistan vs. Canada in the US

Overall Sentiment: Neutral
```

## Future Improvements

- Postgres storage for persistent task results
- Streaming responses for real-time output
- Multi-language news support