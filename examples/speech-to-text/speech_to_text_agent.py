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
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_data,
                            "format": ext.strip(".") if ext else "wav"
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
    # Extract the user's message
    if not messages:
        return "No messages received."

    last_message = messages[-1]
    content = last_message.get("content", "")

    user_query = ""
    temp_file_path = None

    if isinstance(content, str):
        user_query = content
    elif isinstance(content, list):
        # Handle multimodal content (text + files)
        for part in content:
            if part.get("type") == "text":
                user_query += part.get("text", "") + " "
            elif part.get("type") == "image_url":
                # Extract file data (MessageConverter maps all files to image_url)
                url = part.get("image_url", {}).get("url", "")
                if url.startswith("data:"):
                    try:
                        header, encoded = url.split("base64,", 1)
                        mime_type = header.split(":")[1].split(";")[0]
                        file_ext = ".bin"
                        if "audio/wav" in mime_type: file_ext = ".wav"
                        elif "audio/mpeg" in mime_type: file_ext = ".mp3"
                        elif "audio/ogg" in mime_type: file_ext = ".ogg"
                        elif "audio/mp4" in mime_type: file_ext = ".m4a"
                        
                        # Save to temp file
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as f:
                            f.write(base64.b64decode(encoded))
                            temp_file_path = f.name
                        
                        user_query += f"\n\nUser uploaded an audio file: {temp_file_path}. Please use the transcribe_audio tool to process this specific file."
                    except Exception as e:
                        user_query += f"\n\nError processing attachment: {str(e)}"

    # Run the Agno agent
    result = agent.run(user_query)
    
    # Cleanup temp file if needed (optional, or rely on OS/restart)
    # if temp_file_path and os.path.exists(temp_file_path):
    #    os.unlink(temp_file_path)

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
