import os
import logging
try:
    from agno.agent import Agent
    from agno.models.azure import AzureOpenAI
    AGNO_AVAILABLE = True
except ImportError:
    # Fallback to direct OpenAI usage
    from openai import AzureOpenAI as AzureOpenAIClient
    Agent = None
    AzureOpenAI = None
    AGNO_AVAILABLE = False

from app.core.config import settings

logger = logging.getLogger("bindu_agent")

class BinduAgentService:
    def __init__(self):
        self.agent = None
        self.client = None
        self._setup_agent()
    
    def _setup_agent(self):
        # Common Envs
        os.environ["AZURE_OPENAI_API_KEY"] = settings.AZURE_GPT_API_KEY
        os.environ["AZURE_OPENAI_ENDPOINT"] = settings.AZURE_GPT_ENDPOINT
        os.environ["AZURE_OPENAI_API_VERSION"] = settings.AZURE_GPT_API_VERSION or "2023-05-15"

        if AGNO_AVAILABLE:
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
                logger.info(f"Bindu Agent '{settings.AGENT_NAME}' initialized (Agno).")
            except Exception as e:
                logger.error(f"Failed to initialize Agno agent: {e}")
                self.agent = None
        
        if not self.agent:
            # Fallback initialization
            logger.info("Initializing fallback Azure OpenAI client...")
            try:
                self.client = AzureOpenAIClient(
                    azure_endpoint=settings.AZURE_GPT_ENDPOINT,
                    api_key=settings.AZURE_GPT_API_KEY,
                    api_version=settings.AZURE_GPT_API_VERSION or "2023-05-15"
                )
            except Exception as e:
                logger.error(f"Failed to init fallback client: {e}")

    def run(self, message: str, context: str = "") -> str:
        """Run the agent and return clean text response."""
        full_message = message
        if context:
            full_message = f"Context file content:\n```\n{context}\n```\n\nUser Question: {message}"

        # 1. Try Agno
        if self.agent:
            try:
                response = self.agent.run(full_message)
                if hasattr(response, 'content'):
                    return str(response.content)
                return str(response)
            except Exception as e:
                logger.error(f"Agno agent run failed: {e}")
        
        # 2. Try Fallback Client
        if self.client:
            try:
                response = self.client.chat.completions.create(
                    model=settings.GPT_DEPLOYMENT or "gpt-4o", # fallback model name if empty
                    messages=[
                        {"role": "system", "content": "You are a Bindu Node Agent. Be helpful and concise."},
                        {"role": "user", "content": full_message}
                    ]
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Fallback agent run failed: {e}")
                return f"Error executing agent (Fallback): {str(e)}"

        return f"[Error] No AI backend available. Please check AZURE_GPT keys in .env. (Agno missing, Fallback failed)"
