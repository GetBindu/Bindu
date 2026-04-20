# Kotlin OpenAI Agent

An assistant built with Kotlin and the [Bindu Kotlin SDK](../../sdks/kotlin/).

## Prerequisites

- JDK 17+
- Python >= 3.12 with Bindu installed (`pip install bindu[grpc]`)
- OpenAI API key

## Setup

```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

## Run

```bash
./gradlew run
```

## Send a message

```bash
curl -X POST http://localhost:3773 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Explain coroutines in Kotlin"}],
        "messageId": "msg-1",
        "contextId": "ctx-1",
        "taskId": "task-1"
      }
    },
    "id": "1"
  }'
```
