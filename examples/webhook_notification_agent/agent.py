"""
Push Notification Webhook Agent for Bindu AI Framework

Example agent that sends webhook notifications when tasks complete.
Demonstrates event-driven integration with external systems.
"""

from typing import Any, Dict, List
import os
import json
import uuid
import requests
from datetime import datetime

from bindu.penguin.bindufy import bindufy


CONFIG = {
    "name": "webhook_notification_agent",
    "description": "Example Bindu agent that sends a webhook notification when a task completes.",
    "author": "Mayur Ughade",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": False
    },
    "skills": []
}


# Webhook Configuration (environment variables with defaults)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook")
WEBHOOK_TIMEOUT = int(os.getenv("WEBHOOK_TIMEOUT", "5"))


def send_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send webhook notification to external system.
    
    Args:
        payload: Dictionary containing event data
    
    Returns:
        Dictionary with status and result information
    """
    try:
        response = requests.post(
            WEBHOOK_URL,
            json=payload,
            timeout=WEBHOOK_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()

        return {
            "status": "sent",
            "status_code": response.status_code
        }

    except requests.exceptions.Timeout:
        return {
            "status": "failed",
            "error": "webhook_timeout"
        }

    except requests.exceptions.RequestException as e:
        return {
            "status": "failed",
            "error": f"http_error: {str(e)}"
        }

    except Exception as e:
        return {
            "status": "failed",
            "error": str(e)
        }


def handler(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Official Bindu handler contract.
    
    Receives messages, processes them, and sends a webhook notification.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
    
    Returns:
        Dictionary with status and response data
    """
    try:
        # Input validation
        if not messages:
            return {
                "status": "error",
                "error": "no_messages_provided"
            }

        user_message = messages[-1].get("content")

        if not user_message:
            return {
                "status": "error",
                "error": "no_message_content"
            }

        request_id = str(uuid.uuid4())

        # Build event payload
        event_payload = {
            "event": "task_completed",
            "request_id": request_id,
            "message": user_message,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "agent": CONFIG["name"]
        }

        # Send webhook
        webhook_result = send_webhook(event_payload)

        return {
            "status": "success",
            "response": {
                "request_id": request_id,
                "webhook": webhook_result
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# Register the agent with Bindu
bindufy(CONFIG, handler)


if __name__ == "__main__":
    # Test the agent locally
    print(f"Testing {CONFIG['name']}...")
    print("-" * 50)
    
    test_messages = [
        {"role": "user", "content": "Process this webhook test task"}
    ]
    
    result = handler(test_messages)
    print("\nAgent Response:")
    print(json.dumps(result, indent=2))
