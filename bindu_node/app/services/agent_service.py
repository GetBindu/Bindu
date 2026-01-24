import os
import logging
try:
    from agno.agent import Agent
    from agno.models.azure import AzureOpenAI
    AGNO_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Agno Import Error: {e}")
    Agent = AzureOpenAI = None
    AGNO_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger("bindu_agent")

class BinduAgentService:
    def __init__(self):
        self.agent = None
        self._setup_agent()
    
    def _setup_agent(self):
        if not AGNO_AVAILABLE:
            logger.warning("Agno not installed. Running in dummy mode.")
            return

        # Ensure env vars are set for agno/openai
        os.environ["AZURE_OPENAI_API_KEY"] = settings.AZURE_GPT_API_KEY
        os.environ["AZURE_OPENAI_ENDPOINT"] = settings.AZURE_GPT_ENDPOINT
        os.environ["AZURE_OPENAI_API_VERSION"] = settings.AZURE_GPT_API_VERSION
        
        try:
            self.agent = Agent(
                name=settings.AGENT_NAME,
                instructions=(
                    "You are a Bindu Node Agent. You are part of the Internet of Agents. "
                    "You identify yourself as part of the Bindu network. "
                    "Be concise, professional, and helpful."
                ),
                model=AzureOpenAI(
                    id=settings.GPT_DEPLOYMENT,
                    api_key=settings.AZURE_GPT_API_KEY,
                    azure_endpoint=settings.AZURE_GPT_ENDPOINT,
                    api_version=settings.AZURE_GPT_API_VERSION,
                )
            )
            logger.info(f"Bindu Agent '{settings.AGENT_NAME}' initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize agent: {e}")

    def run(self, message: str, context: str = "") -> str:
        """Run the agent and return clean text response."""
        full_message = message
        if context:
            full_message = f"Context file content:\n```\n{context}\n```\n\nUser Question: {message}"

        if not self.agent:
            return f"[Dummy Mode] Echo: {message} (Install 'agno' for real AI)"
        
        try:
            response = self.agent.run(full_message)
            # Extract clean content from RunOutput if possible
            if hasattr(response, 'content'):
                return str(response.content)
            return str(response)
        except Exception as e:
            logger.error(f"Agent run failed: {e}")
            return f"Error executing agent: {str(e)}"
