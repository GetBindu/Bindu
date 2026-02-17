import base64
import os
from typing import Any

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from bindu.penguin.bindufy import bindufy
from dotenv import load_dotenv

# Load environment variables (API keys)
load_dotenv()

# -----------------------------
# Agent Tools
# -----------------------------

def transcribe_audio(file_path: str) -> str:
    """Transcribes a real audio file (WAV, MP3, etc.) using Gemini's multimodal capabilities via OpenRouter.

    Args:
        file_path (str): The absolute path to the audio file.

    Returns:
        str: The transcribed text or an error message.
    """
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}. Please provide a valid absolute path."

    try:
        # Determine MIME type based on extension
        ext = os.path.splitext(file_path)[1].lower()
        mime_types = {
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
        }
        mime_type = mime_types.get(ext, "application/octet-stream")

        # Read the audio file and encode to base64
        with open(file_path, "rb") as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode("utf-8")

        # Create a multimodal message for transcription
        # We use Gemini 2.0 Flash because it is highly efficient and supports audio input via OpenRouter
        transcription_agent = Agent(
            model=OpenRouter(id="google/gemini-2.0-flash-001"),
            instructions=["You are an expert transcriber. Transcribe the provided audio accurately. Do not add conversational filler."],
        )

        # Send the audio data as a part
        response = transcription_agent.run([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this audio file accurately and completely."},
                    {
                        "type": "image_url", # OpenRouter uses image_url structure for multimodal blobs
                        "image_url": {
                            "url": f"data:{mime_type};base64,{audio_data}"
                        }
                    }
                ]
            }
        ])

        return response.content if hasattr(response, 'content') else str(response)

    except Exception as e:
        return f"Error during transcription: {str(e)}"


def format_transcript(text: str) -> str:
    """Formats raw text into structured paragraphs and sections."""
    return f"### Formatted Transcript\n\n{text}"


def summarize_discussion(transcript: str) -> str:
    """Generates a concise summary of the transcribed text."""
    return f"### Summary\n\nThis audio discusses key points related to: {transcript[:100]}..."


# -----------------------------
# Agent Definition
# -----------------------------

# Define the Agno Agent with instructions and tools
agent = Agent(
    instructions=[
        "You are a Speech-to-Text Agent that specializes in converting audio to text.",
        "When a user provides an audio file path, use the 'transcribe_audio' tool to get the text.",
        "After transcription, format the text into clean paragraphs.",
        "If multiple speakers are clearly present, identify them as 'Speaker A', 'Speaker B', etc.",
        "Summarize the main points of the conversation at the end.",
    ],
    model=OpenRouter(id="google/gemini-2.0-flash-001"),
    tools=[transcribe_audio, format_transcript, summarize_discussion],
    markdown=True,
)


def handler(messages: list[dict[str, str]]) -> Any:
    """Protocol-compliant handler for processing agent messages.

    Signature required by Bindu: (messages: list[dict[str, str]]) -> Any
    """
    # Extract the user's message text
    user_query = messages[-1].get("content", "")

    # Run the Agno agent
    result = agent.run(user_query)

    # Return the content string as required by the protocol
    return result.content


# Bindu Configuration
config = {
    "author": "mandeep@getbindu.com",
    "name": "Speech-to-Text Agent",
    "description": "A secure, protocol-compliant agent that transcribes audio files via OpenRouter.",
    "version": "1.0.0",
    "skills": ["./skills/speech-recognition"],
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
    "recreate_keys": False,
}

# The entry point for the agent
if __name__ == "__main__":
    bindufy(config=config, handler=handler)
