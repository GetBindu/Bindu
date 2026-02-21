import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3"


def call_llm(prompt: str) -> str:
    data = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=180)
        response.raise_for_status()

        return response.json().get("response", "").strip()

    except Exception as e:
        return f"Error: {str(e)}"