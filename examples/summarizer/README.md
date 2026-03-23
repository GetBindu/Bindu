# Text Summarizer Agent

A professional Bindu agent that creates concise, coherent summaries of any input text using OpenRouter's `openai/gpt-oss-120b` model.

## What is This?

This is a **text summarization agent** that:
- Creates clear, concise summaries of any input text
- Preserves key information and context
- Uses OpenRouter's advanced `openai/gpt-oss-120b` model
- Provides rapid, high-quality text condensation
- Demonstrates Bindu's text transformation capabilities

## Features

- **Intelligent Summarization**: Context-aware content condensation
- **Key Point Preservation**: Maintains essential information
- **Coherent Output**: Well-structured, readable summaries
- **Fast Processing**: Optimized for quick text analysis
- **Multi-Format Support**: Handles various text types and structures

## Quick Start

### Prerequisites
- Python 3.12+
- OpenRouter API key
- uv package manager
- Bindu installed in project root

### 1. Set Environment Variables

Create `.env` file in `examples/summarizer/`:

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

### 3. Start the Summarizer Agent

```bash
# From Bindu root directory
cd examples/summarizer
uv run python summarizer_agent.py
```

The agent will start on `http://localhost:3774`

### 4. Test the Summarizer

Open your browser to `http://localhost:3774/docs` and use the chat interface, or:

```bash
curl -X POST http://localhost:3774/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Climate change refers to long-term shifts in global temperatures and weather patterns. While climate variations are natural, human activities have been the main driver of climate change since the mid-20th century, primarily due to fossil fuel burning, which increases heat-trapping greenhouse gas levels in Earth's atmosphere. This is raising average temperatures and causing more frequent and intense extreme weather events."}],
        "kind": "message",
        "messageId": "msg-001",
        "contextId": "ctx-001",
        "taskId": "task-001"
      },
      "configuration": {"acceptedOutputModes": ["application/json"]}
    },
    "id": "1"
  }'
```

## Architecture

### File Structure

```
examples/summarizer/
├── summarizer_agent.py              # Main Agno agent with OpenRouter
├── skills/
│   └── text-summarization-skill/
│       └── skill.yaml              # Bindu skill definition
├── .env.example                    # Environment variables template
└── README.md                       # This documentation
```

### Agent Configuration

```python
agent = Agent(
    instructions="You are a professional summarization assistant...",
    model=OpenRouter(id="openai/gpt-oss-120b")
)
```

### Model Configuration

- **Provider**: OpenRouter
- **Model**: `openai/gpt-oss-120b`
- **Temperature**: Default (balanced for summarization)
- **API**: OpenRouter's API endpoint

## Skills Integration

The summarizer includes a Bindu skill definition with:

- **Skill ID**: `text-summarization-skill`
- **Capabilities**: Text summarization, key point extraction, context preservation
- **Input/Output**: JSON format for structured data exchange
- **Tags**: summarization, text-processing, content-condensation, productivity

## Example Interactions

### Sample Input
```
"Climate change refers to long-term shifts in global temperatures and weather patterns. While climate variations are natural, human activities have been the main driver of climate change since the mid-20th century, primarily due to fossil fuel burning, which increases heat-trapping greenhouse gas levels in Earth's atmosphere. This is raising average temperatures and causing more frequent and intense extreme weather events."
```

### Sample Output
```
"Climate change involves long-term shifts in global temperatures and weather patterns, with human activities becoming the primary driver since the mid-20th century through fossil fuel burning. This has increased greenhouse gas levels in Earth's atmosphere, leading to rising temperatures and more frequent extreme weather events."
```

## Development

### Modifying the Agent

1. **Change instructions**: Edit the `instructions` parameter
2. **Adjust summary length**: Modify the prompt to specify different length requirements
3. **Update model**: Change the OpenRouter model ID if needed
4. **Enhance skills**: Update `skills/text-summarization-skill/skill.yaml`

### Example Customization

```python
# For longer summaries
instructions="Create detailed 4-5 sentence summaries that preserve important details..."

# For bullet-point summaries
instructions="Summarize the text using bullet points for key information..."

# For specific domain summarization
instructions="You are a scientific summarizer. Create summaries suitable for academic papers..."
```

## Use Cases

### Academic & Research
- Research paper summarization
- Literature review condensation
- Abstract generation

### Business & Professional
- Report summarization
- Meeting transcript condensation
- Email thread summaries

### Content & Media
- Article summarization
- Document analysis
- Content curation

### Personal Productivity
- Reading assistance
- Information processing
- Study aid

## Dependencies

All dependencies are managed through the root `pyproject.toml`:

```bash
# Core dependencies already included in bindu project
agno>=2.4.8
langchain>=1.2.9
langchain-openai>=1.1.8
python-dotenv>=1.1.0
```

## Performance

### Typical Processing Time
- **Short texts** (< 500 words): 1-2 seconds
- **Medium texts** (500-1000 words): 2-4 seconds
- **Long texts** (> 1000 words): 4-8 seconds

### Quality Metrics
- **Coherence**: High - maintains logical flow
- **Accuracy**: Excellent - preserves key information
- **Conciseness**: Optimized - 2-3 sentence summaries
- **Readability**: Professional - clear and well-structured

## Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Verify OPENROUTER_API_KEY is set
   - Check key validity and credits
   - Ensure OpenRouter service is available

2. **Poor Summaries**:
   - Review input text quality
   - Check for complex or ambiguous content
   - Consider adjusting instructions

3. **Slow Response**:
   - Check network connectivity
   - Monitor API rate limits
   - Consider text length optimization

### Best Practices

- **Input Quality**: Provide clear, well-structured text for best results
- **Length Limits**: Very long texts may be better split into sections
- **Context**: Include relevant context when summarizing specialized content
- **Review**: Always review summaries for critical applications

## Contributing

To extend this example:

1. **Add new summarization styles**: Bullet points, different lengths
2. **Multi-language support**: Add language detection and translation
3. **Domain-specific modes**: Academic, business, casual summarization
4. **Quality metrics**: Add automatic quality assessment
5. **Batch processing**: Support multiple text summarization

## License

This example is part of the Bindu framework and follows the same license terms.
