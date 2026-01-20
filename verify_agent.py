import requests
import json
import uuid

def test_agent():
    url = "http://localhost:3773/"
    
    # Valid JSON-RPC 2.0 Payload matching Bindu Protocol
    msg_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [
                    {
                        "kind": "text",
                        "text": "Analyze Tesla"
                    }
                ],
                "kind": "message",
                "messageId": msg_id,
                "contextId": msg_id, # New context
                "taskId": str(uuid.uuid4())
            },
            "configuration": {
                "acceptedOutputModes": ["application/json"]
            }
        },
        "id": msg_id
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print(f"📡 Sending request to {url}...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"✅ Status Code: {response.status_code}")
        
        data = response.json()
        
        # Extract the assistant's reply from the nested structure
        # The structure is usually result -> history -> last message -> content/parts
        if "result" in data:
            print("\n📄 Response Body:")
            print(json.dumps(data, indent=2))
        else:
            print("\n❌ Error Response:")
            print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    test_agent()
