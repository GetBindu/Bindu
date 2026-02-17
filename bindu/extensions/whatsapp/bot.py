from typing import Optional
from loguru import logger
from wa_cloud import Bot
from bindu.settings import Settings


class BinduWhatsAppBot:
    """WhatsApp bot wrapper for Bindu agents."""
    
    def __init__(self, settings: Optional[Settings] = None):
        
        self.settings = settings or Settings()
        self.whatsapp_config = self.settings.whatsapp
        
        # Validate configuration
        if not self.whatsapp_config.enabled:
            logger.warning("WhatsApp integration is disabled in settings")
            self.bot = None
            return
            
        if not self.whatsapp_config.access_token:
            raise ValueError("WhatsApp access token not configured")
            
        if not self.whatsapp_config.phone_number_id:
            raise ValueError("WhatsApp phone number ID not configured")
        
        # Initialize py-whatsapp-cloudbot
        self.bot = Bot(
            access_token=self.whatsapp_config.access_token,
            phone_number_id=self.whatsapp_config.phone_number_id,
        )
        
        logger.info(
            f"WhatsApp bot initialized with phone number ID: "
            f"{self.whatsapp_config.phone_number_id}"
        )
    
    def send_message(self, to: str, message: str) -> dict:
        if not self.bot:
            raise ValueError("WhatsApp bot is not initialized")
        
        logger.info(f"Sending WhatsApp message to {to}")
        
        try:
            response = self.bot.send_message(
                recipient_id=to,
                message=message
            )
            logger.debug(f"WhatsApp API response: {response}")
            return response
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Check if WhatsApp integration is enabled and configured."""
        return self.bot is not None