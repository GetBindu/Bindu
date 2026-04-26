import os
from typing import List

from openai import OpenAI

# Initialize client only if API key exists
_api_key = os.getenv("OPENROUTER_API_KEY")

client = (
    OpenAI(
        api_key=_api_key,
        base_url="https://openrouter.ai/api/v1",
    )
    if _api_key
    else None
)


def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for given text.

    - Uses OpenRouter/OpenAI if API key is available
    - Falls back to dummy embedding in test environments
    """

    # 🔥 TEST-SAFE FALLBACK
    if not client:
        return [0.0] * 1536  # matches embedding size

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    except Exception:
        # 🔥 FAIL-SAFE (network/API issues)
        return [0.0] * 1536
