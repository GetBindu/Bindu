"""
WhatsApp Webhook Endpoint

Handles incoming webhook requests from Meta's WhatsApp Cloud API.
Supports webhook verification and message processing.
"""

from typing import Any, Dict
from starlette.requests import Request
from starlette.responses import Response, PlainTextResponse
from loguru import logger
from bindu.settings import Settings


class WhatsAppWebhook:
    """Handles WhatsApp webhook verification and message processing."""
    
    def __init__(self, settings: Settings):
        """
        Initialize webhook handler.
        
        Args:
            settings: Bindu settings instance
        """
        self.settings = settings
        self.whatsapp_config = settings.whatsapp
    
    async def verify(self, request: Request) -> Response:
        """
        Handle webhook verification (GET request from Meta).
        
        Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
        We verify the token and return the challenge to confirm the webhook.
        
        Args:
            request: Incoming HTTP request
            
        Returns:
            PlainTextResponse with challenge or error
        """
        params = request.query_params
        
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge")
        
        logger.info(f"Webhook verification request: mode={mode}")
        
        # Check if verification request
        if mode == "subscribe" and token == self.whatsapp_config.verify_token:
            logger.info("Webhook verified successfully")
            return PlainTextResponse(content=challenge, status_code=200)
        else:
            logger.warning(f"Webhook verification failed: invalid token")
            return PlainTextResponse(
                content="Forbidden", 
                status_code=403
            )
    
    async def handle_message(self, request: Request) -> Response:
        """
        Handle incoming WhatsApp message (POST request from Meta).
        
        Args:
            request: Incoming HTTP request with message payload
            
        Returns:
            Response confirming message was received
        """
        try:
            # Parse JSON payload
            body = await request.json()
            logger.debug(f"Received webhook payload: {body}")
            
            # Extract message data
            messages = self._extract_messages(body)
            
            if not messages:
                logger.debug("No messages found in payload")
                return Response(status_code=200)
            
            # Process each message
            for msg in messages:
                await self._process_message(msg)
            
            return Response(status_code=200)
            
        except Exception as e:
            logger.error(f"Error handling webhook message: {e}")
            return Response(status_code=500)
    
    def _extract_messages(self, payload: Dict[str, Any]) -> list:
        """
        Extract messages from WhatsApp webhook payload.
        
        Args:
            payload: Webhook JSON payload
            
        Returns:
            List of message dictionaries
        """
        messages = []
        
        try:
            # WhatsApp payload structure:
            # {
            #   "object": "whatsapp_business_account",
            #   "entry": [{
            #     "changes": [{
            #       "value": {
            #         "messages": [{ ... }]
            #       }
            #     }]
            #   }]
            # }
            
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    msgs = value.get("messages", [])
                    
                    for msg in msgs:
                        # Extract relevant fields
                        messages.append({
                            "from": msg.get("from"),
                            "id": msg.get("id"),
                            "type": msg.get("type"),
                            "text": msg.get("text", {}).get("body", ""),
                            "timestamp": msg.get("timestamp"),
                        })
            
        except Exception as e:
            logger.error(f"Error extracting messages: {e}")
        
        return messages
    
    async def _process_message(self, message: Dict[str, Any]):
        """
        Process a single WhatsApp message.
        
        This is where we'll integrate with Bindu agents.
        For now, just log the message.
        
        Args:
            message: Message dictionary
        """
        sender = message.get("from")
        text = message.get("text")
        
        logger.info(f"Processing message from {sender}: {text}")
        
        # TODO: In next iteration, route to Bindu agent
        # - Create task for agent
        # - Get agent response
        # - Send reply via WhatsApp bot