"""Simple FastAPI webhook receiver for Bindu agent notifications.

Run with: python webhook_client_example.py
"""

from fastapi import FastAPI, Request, Header, HTTPException
import uvicorn

# Configuration
WEBHOOK_TOKEN = "secret_abc123"

app = FastAPI()


@app.post("/webhooks/task-updates")
async def handle_task_update(request: Request, authorization: str = Header(None)):
    """Handle webhook notifications from Bindu agent.

    This endpoint receives push notifications for task state changes
    and artifact generation.
    """
    # Verify authentication token
    expected_token = f"Bearer {WEBHOOK_TOKEN}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Parse event
    event = await request.json()

    print(f"\n{'=' * 60}")
    print("Received webhook notification:")
    print(f"Event ID: {event['event_id']}")
    print(f"Sequence: {event['sequence']}")
    print(f"Kind: {event['kind']}")
    print(f"Task ID: {event['task_id']}")

    # Handle different event types
    if event["kind"] == "status-update":
        state = event["status"]["state"]
        is_final = event["final"]

        print(f"Status: {state}")
        print(f"Final: {is_final}")

        if is_final:
            if state == "completed":
                print("✅ Task completed successfully!")
            elif state == "failed":
                print("❌ Task failed!")
            elif state == "canceled":
                print("⚠️  Task canceled!")

    elif event["kind"] == "artifact-update":
        artifact = event["artifact"]
        artifact_name = artifact.get("name", "unnamed")

        print(f"Artifact: {artifact_name}")
        print(f"Artifact ID: {artifact['artifact_id']}")

        # Process artifact data
        if "parts" in artifact:
            for part in artifact["parts"]:
                if part["kind"] == "text":
                    print(f"Text content: {part['text'][:100]}...")
                elif part["kind"] == "data":
                    print(f"Data content: {part['data']}")

    print(f"{'=' * 60}\n")

    return {"status": "received"}


if __name__ == "__main__":
    print("Starting webhook receiver on http://0.0.0.0:8000")
    print("Webhook endpoint: http://0.0.0.0:8000/webhooks/task-updates")
    print(f"Expected token: Bearer {WEBHOOK_TOKEN}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
