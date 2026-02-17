from starlette.requests import Request
from starlette.responses import Response
from loguru import logger
from bindu.extensions.whatsapp import WhatsAppWebhook, BinduWhatsAppBot
from bindu.server.applications import BinduApplication

async def whatsapp_webhook_verify(app: BinduApplication, request: Request) -> Response:
    """
    Handle WhatsApp webhook verification (GET request).
    
    Meta sends a GET request to verify the webhook endpoint.
    We validate the verify_token and return the challenge.
    """
    from bindu.settings import Settings
    
    settings = Settings()
    webhook = WhatsAppWebhook(settings)
    return await webhook.verify(request)


async def whatsapp_webhook_message(app: BinduApplication, request: Request) -> Response:
    """
    Handle incoming WhatsApp messages (POST request).
    
    Meta sends POST requests with message payloads.
    We process the messages and can route them to agents.
    """
    from bindu.settings import Settings
    
    settings = Settings()
    webhook = WhatsAppWebhook(settings)
    return await webhook.handle_message(request)