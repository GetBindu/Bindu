import requests
import json
import uuid
import time

def test_agent_with_polling(query):
    print(f"\n🌍 Testing Query: '{query}'")
    url = "http://localhost:3773/"
    msg_id = str(uuid.uuid4())
    
    # 1. Send the Request
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": f"Analyze {query}"}],
                "kind": "message",
                "messageId": msg_id,
                "contextId": msg_id,
                "taskId": str(uuid.uuid4())
            },
            "configuration": {"acceptedOutputModes": ["application/json"]}
        },
        "id": msg_id
    }
    
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    if "result" not in data:
        print("❌ Failed to submit task")
        return

    task_id = data["result"]["id"]
    print(f"✅ Submitted. Waiting for agent to resolving symbol...")
    
    # 2. Poll for Result
    for _ in range(20): # increased timeout for search
        time.sleep(1)
        
        poll_payload = {
            "jsonrpc": "2.0",
            "method": "tasks/get",
            "params": {"taskId": task_id},
            "id": str(uuid.uuid4())
        }
        
        poll_res = requests.post(url, json=poll_payload, headers=headers)
        poll_data = poll_res.json()
        
        status = poll_data["result"]["status"]["state"]
        
        if status == "completed":
            # Find the assistant's message in history
            history = poll_data["result"]["history"]
            for msg in reversed(history):
                if msg["role"] == "assistant":
                    for part in msg["parts"]:
                        if part["kind"] == "text":
                            print("\n📝 AGENT RESPONSE:")
                            print("-" * 40)
                            print(part["text"])
                            print("-" * 40)
                    return
        
        if status == "failed":
            print("❌ Task Failed.")
            return

    print("⚠️ Timed out.")

if __name__ == "__main__":
    # Interactive Mode
    print("Welcome to the Financial Agent Test Console! 🚀")
    while True:
        try:
            user_input = input("\nEnter a stock name to analyze (or 'exit'): ").strip()
            if user_input.lower() == 'exit':
                break
            if user_input:
                test_agent_with_polling(user_input)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
