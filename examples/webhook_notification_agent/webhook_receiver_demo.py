"""
Webhook Receiver Demo Server

A simple Flask server to receive and display webhook notifications
from the Bindu webhook notification agent.

This demo server helps you test the webhook agent locally without
needing external webhook services.
"""

import json
from datetime import datetime

from flask import Flask, request, jsonify


app = Flask(__name__)


# Store received webhooks in memory for demo purposes
webhook_history = []


@app.route("/webhook", methods=["POST"])
def webhook_endpoint():
    """
    Webhook endpoint that receives POST requests from the agent.
    
    Returns:
        JSON response with acknowledgment
    """
    try:
        # Get the webhook payload
        payload = request.get_json()
        
        if not payload:
            return jsonify({
                "status": "error",
                "message": "No JSON payload received"
            }), 400
        
        # Log the received webhook
        received_at = datetime.utcnow().isoformat() + "Z"
        webhook_entry = {
            "received_at": received_at,
            "payload": payload
        }
        webhook_history.append(webhook_entry)
        
        # Print webhook details to console
        print("\n" + "=" * 70)
        print(f"📬 WEBHOOK RECEIVED at {received_at}")
        print("=" * 70)
        print(f"Event:      {payload.get('event', 'N/A')}")
        print(f"Message:    {payload.get('message', 'N/A')}")
        print(f"Timestamp:  {payload.get('timestamp', 'N/A')}")
        print(f"Request ID: {payload.get('request_id', 'N/A')}")
        print(f"Agent:      {payload.get('agent', 'N/A')}")
        
        if payload.get('metadata'):
            print("\nMetadata:")
            print(json.dumps(payload['metadata'], indent=2))
        
        print("=" * 70 + "\n")
        
        # Return acknowledgment
        return jsonify({
            "status": "success",
            "message": "Webhook received successfully",
            "received_at": received_at
        }), 200
        
    except Exception as e:
        print(f"\n✗ Error processing webhook: {type(e).__name__} - {str(e)}\n")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/history", methods=["GET"])
def get_history():
    """
    Get the history of received webhooks.
    
    Returns:
        JSON array of all received webhooks
    """
    return jsonify({
        "total": len(webhook_history),
        "webhooks": webhook_history
    })


@app.route("/clear", methods=["POST"])
def clear_history():
    """
    Clear the webhook history.
    
    Returns:
        JSON response with confirmation
    """
    global webhook_history
    count = len(webhook_history)
    webhook_history = []
    
    print(f"\n🗑️  Cleared {count} webhook(s) from history\n")
    
    return jsonify({
        "status": "success",
        "message": f"Cleared {count} webhook(s)"
    })


@app.route("/", methods=["GET"])
def index():
    """
    Simple index page with server info.
    
    Returns:
        JSON with server status
    """
    return jsonify({
        "service": "Webhook Receiver Demo",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook (POST)",
            "history": "/history (GET)",
            "clear": "/clear (POST)"
        },
        "webhooks_received": len(webhook_history)
    })


def main():
    """
    Start the webhook receiver demo server.
    """
    print("\n" + "=" * 70)
    print("🚀 Starting Webhook Receiver Demo Server")
    print("=" * 70)
    print("\nEndpoints:")
    print("  • POST   http://localhost:5000/webhook  - Receive webhooks")
    print("  • GET    http://localhost:5000/history  - View webhook history")
    print("  • POST   http://localhost:5000/clear    - Clear history")
    print("  • GET    http://localhost:5000/         - Server info")
    print("\n" + "=" * 70)
    print("Waiting for webhooks...\n")
    
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )


if __name__ == "__main__":
    main()
