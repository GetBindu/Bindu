"""Embedding generation for semantic memory.

Uses the OpenAI-compatible embeddings API via OpenRouter.
The ``openai`` package is an optional dependency — install it with::

    pip install bindu[semantic-memory]

or directly::

    pip install openai
"""

from __future__ import annotations

from typing import List


def get_embedding(text: str, api_key: str | None = None, base_url: str | None = None) -> List[float]:
    """Generate a vector embedding for the given text.

    Uses ``text-embedding-3-small`` via OpenRouter by default.
    Requires the ``openai`` package and a valid ``OPENROUTER_API_KEY``
    environment variable (or explicit ``api_key`` argument).

    Args:
        text: The text to embed.
        api_key: Optional API key override. Falls back to
            ``OPENROUTER_API_KEY`` environment variable.
        base_url: Optional base URL override. Defaults to
            ``https://openrouter.ai/api/v1``.

    Returns:
        A list of floats representing the text embedding.

    Raises:
        ImportError: If the ``openai`` package is not installed.
        ValueError: If no API key is available.
        RuntimeError: If the embedding API call fails.
    """
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError(
            "The 'openai' package is required for semantic memory embeddings. "
            "Install it with: pip install openai\n"
            "Or install the optional group: pip install bindu[semantic-memory]"
        ) from exc

    import os

    resolved_key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not resolved_key:
        raise ValueError(
            "No API key found for embeddings. Set OPENROUTER_API_KEY or OPENAI_API_KEY "
            "environment variable, or pass api_key explicitly."
        )

    resolved_url = base_url or "https://openrouter.ai/api/v1"

    client = OpenAI(api_key=resolved_key, base_url=resolved_url)

    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
    except Exception as exc:
        raise RuntimeError(
            f"Embedding API call failed: {exc}. "
            "Check your API key and network connectivity."
        ) from exc

    return response.data[0].embedding