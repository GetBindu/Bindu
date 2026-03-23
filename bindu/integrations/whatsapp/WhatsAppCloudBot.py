import requests
import os

class WhatsAppCloudBot:
    """
    WhatsApp Cloud API Integration for Bindu Agents.
    Enables agents to interact with users directly via WhatsApp.
    """
    def __init__(self):
        self.api_url = "https://graph.facebook.com/v17.0"
        self.access_token = os.getenv("WHATSAPP_TOKEN")
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_ID")

    def send_message(self, to, text):
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }
        return requests.post(url, headers=headers, json=payload)
