import os
from typing import Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()

class Settings(BaseModel):
    # App Settings
    APP_NAME: str = "Bindu Agent Node"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Paths
    # Current file is in bindu_node/app/core/config.py
    # We want BASE_DIR to be the repository root (bindu/)
    # .. -> app/core -> app
    # .. -> app -> bindu_node
    # .. -> bindu_node -> bindu (root)
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    
    # Azure OpenAI
    AZURE_GPT_ENDPOINT: str = os.getenv("AZURE_GPT_ENDPOINT", "")
    AZURE_GPT_API_KEY: str = os.getenv("AZURE_GPT_API_KEY", "")
    AZURE_GPT_API_VERSION: str = os.getenv("AZURE_GPT_API_VERSION", "2024-12-01-preview")
    GPT_DEPLOYMENT: str = os.getenv("GPT_DEPLOYMENT", "gpt-5-chat")
    
    # Bindu Agent Identity (Simulated)
    AGENT_NAME: str = os.getenv("AGENT_NAME", "Bindu-Node-01")
    AGENT_ID: str = "agent-local-" + os.urandom(4).hex()

    def validate_azure(self):
        """Check if Azure credentials are present."""
        if not self.AZURE_GPT_ENDPOINT or not self.AZURE_GPT_API_KEY:
            return False
        return True

settings = Settings()
