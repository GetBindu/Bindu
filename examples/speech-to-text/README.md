# Speech-to-Text Agent

A multimodal Bindu agent that transcribes real audio files (MP3, WAV, OGG, M4A) using Gemini 2.0 Flash via OpenRouter.

## What is This?

This is a **speech-to-text agent** that:
- Transcribes real audio files using Gemini's multimodal capabilities
- Formats transcripts into clean, structured paragraphs
- Identifies multiple speakers when present
- Generates concise summaries of transcribed content
- Uses only the `OPENROUTER_API_KEY` — no extra transcription services needed

## Features

- **Real Audio Transcription**: Processes MP3, WAV, OGG, and M4A files via base64 encoding
- **Multimodal AI**: Leverages Gemini 2.0 Flash for high-fidelity audio understanding
- **Speaker Identification**: Labels speakers as Speaker A, Speaker B, etc.
- **Auto-Summarization**: Provides a summary of key points after transcription
- **CORS Enabled**: Frontend-ready with `localhost:5173` CORS support
- **Bindu Protocol Compliant**: Full JSON-RPC 2.0 and skill-based discovery

## Quick Start

### Prerequisites
- Python 3.12+
- OpenRouter API key
- uv package manager
- Bindu installed in project root

### 1. Set Environment Variables

Create `.env` file in `examples/speech-to-text/`:

```bash
cp .env.example .env
# Edit .env and add your OpenRouter API key
```

```bash
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

### 2. Install Dependencies

```bash
# From Bindu root directory
uv sync
```

### 3. Start the Agent

```bash
# From Bindu root directory
uv run python examples/speech-to-text/speech_to_text_agent.py
```

The agent will start on `http://localhost:3773`

### 4. Test the Agent

```bash
curl -X POST http://localhost:3773/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Transcribe this audio: C:/path/to/your/audio.mp3"}],
        "kind": "message",
        "messageId": "msg-001",
        "contextId": "ctx-001",
        "taskId": "task-001"
      },
      "configuration": {"acceptedOutputModes": ["text/plain"]}
    },
    "id": "1"
  }'
```

## Architecture

### File Structure

```
examples/speech-to-text/
├── speech_to_text_agent.py          # Main agent with multimodal transcription
├── skills/
│   └── speech-recognition/
│       └── skill.yaml               # Bindu skill definition
├── samples/
│   └── porsche_macan_ad.mp3         # Sample audio for testing
├── .env.example                     # Environment variables template
└── README.md                        # This documentation
```

### Agent Configuration

```python
agent = Agent(
    instructions=["You are a Speech-to-Text Agent..."],
    model=OpenRouter(id="google/gemini-2.0-flash-001"),
    tools=[transcribe_audio, format_transcript, summarize_discussion],
    markdown=True,
)
```

### Model Configuration

- **Provider**: OpenRouter
- **Model**: `google/gemini-2.0-flash-001` (Gemini 2.0 Flash)
- **Multimodal**: Supports audio input via base64 encoding
- **API**: OpenRouter's unified API endpoint

### Tools

| Tool | Description |
|------|-------------|
| `transcribe_audio` | Reads audio file, encodes to base64, sends to Gemini for transcription |
| `format_transcript` | Formats raw text into structured paragraphs |
| `summarize_discussion` | Generates a concise summary of the transcribed content |

## Skills Integration

The agent includes a Bindu skill definition with:

- **Skill ID**: `speech-recognition`
- **Capabilities**: Audio transcription, transcript formatting, content summarization
- **Input**: Audio file path (MP3, WAV, OGG, M4A)
- **Output**: Formatted transcript with summary
- **Tags**: speech-recognition, transcription, audio-processing, multimodal

## Example Interactions

### Sample Audio

A sample audio file is included for testing:

🎧 **Listen**: [`samples/porsche_macan_ad.mp3`](samples/porsche_macan_ad.mp3)

### Sample Input
```
"Transcribe this audio: examples/speech-to-text/samples/porsche_macan_ad.mp3"
```

### Sample Output
```
If the Porsche Macan has proven anything, it's that the days of sacrificing
performance for practicality are gone. Long gone. Engineered to deliver a
driving experience like no other, the Macan has demonstrated excellence in
style and performance to become the leading sports car in its class. So
don't let those five doors fool you. Once you're in the driver's seat, one
thing will become immediately clear. This is a Porsche. The Macan, now
leasing from 3.99%. Conditions apply.

**Summary:**
This audio is an advertisement for the Porsche Macan, highlighting its
combination of performance and practicality, and positioning it as a
leading sports car in its class. It mentions a lease offer at 3.99% with
conditions applying.
```

## Supported Audio Formats

| Format | MIME Type | Extension |
|--------|-----------|-----------|
| MP3 | `audio/mpeg` | `.mp3` |
| WAV | `audio/wav` | `.wav` |
| OGG | `audio/ogg` | `.ogg` |
| M4A | `audio/mp4` | `.m4a` |

## Development

### Modifying the Agent

1. **Change instructions**: Edit the `instructions` parameter in the `Agent` constructor
2. **Add formats**: Update the `mime_types` dictionary in `transcribe_audio`
3. **Update model**: Change the OpenRouter model ID if needed
4. **Enhance skills**: Update `skills/speech-recognition/skill.yaml`

### Example Customization

```python
# For verbatim transcription only (no summary)
instructions = "Transcribe the audio exactly as spoken. Do not summarize."

# For meeting minutes
instructions = "Transcribe the audio and format it as meeting minutes with action items."

# For interview transcription
instructions = "Transcribe the audio, clearly label each speaker, and note timestamps."
```

## Use Cases

### Media & Content
- Podcast transcription
- Interview processing
- Video subtitle generation

### Business & Professional
- Meeting transcription
- Lecture note generation
- Call center analysis

### Accessibility
- Audio-to-text conversion for hearing impaired
- Voice memo transcription
- Audio document digitization

## Dependencies

All dependencies are managed through the root `pyproject.toml`:

```bash
# Core dependencies already included in bindu project
agno>=2.4.8
python-dotenv>=1.1.0
```

## Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Verify `OPENROUTER_API_KEY` is set in `.env`
   - Check key validity and credits on OpenRouter dashboard
   - Ensure the key supports multimodal models (Gemini)

2. **File Not Found**:
   - Use absolute paths for audio files
   - Verify the file exists at the specified path
   - Check file permissions

3. **Unsupported Format**:
   - Ensure the audio file is MP3, WAV, OGG, or M4A
   - Convert other formats using tools like `ffmpeg`

4. **Module Not Found**:
   - Run from the Bindu root directory
   - Run `uv sync` to install dependencies
   - Use: `uv run python examples/speech-to-text/speech_to_text_agent.py`

### Best Practices

- **File Size**: Keep audio files under 20MB for optimal processing
- **Audio Quality**: Clearer audio produces better transcriptions
- **Format**: MP3 is recommended for the best balance of quality and size
- **Paths**: Always use absolute file paths when specifying audio files

## Contributing

To extend this example:

1. **Add new audio formats**: Extend the `mime_types` dictionary
2. **Multi-language support**: Add language detection and translation tools
3. **Streaming transcription**: Implement real-time audio streaming
4. **Speaker diarization**: Enhance speaker identification with timestamps
5. **Batch processing**: Support transcription of multiple files

## License

This example is part of the Bindu framework and follows the same license terms.

---

**Built with 🌻 using the Bindu Agent Framework**
