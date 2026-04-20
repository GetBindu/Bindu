# PDF Research Agent 📄

A powerful document analysis agent that processes PDF files and raw text to generate structured summaries using AI. Built with Bindu framework and OpenRouter integration.

## 🚀 Features

- **PDF Processing**: Extracts text from PDF files automatically
- **Text Analysis**: Summarizes raw document content
- **Flexible Input**: Accepts both file paths and direct text input
- **Structured Output**: Provides clear, concise summaries with key insights
- **Error Handling**: Graceful handling of missing dependencies and file errors
- **Live Service**: Runs as a microservice with DID identity and A2A protocol

## 📋 Prerequisites

- Python 3.12+
- OpenRouter API Key
- Required Python packages

## 🛠️ Installation

### 1. Clone and Navigate
```bash
cd examples
```

### 2. Install Dependencies
```bash
# Using uv (recommended)
uv add bindu agno pypdf python-dotenv

# Or using pip
pip install bindu agno pypdf python-dotenv
```

### 3. Set Up Environment Variables
```bash
# Create .env file
echo "OPENROUTER_API_KEY=your_api_key_here" > .env

# Or export directly
export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
```

## 🎯 Usage

### Running the Agent
```bash
# Start the PDF Research Agent
uv run pdf_research_agent.py

# Or with Python directly
python pdf_research_agent.py
```

The agent will start at `http://localhost:3773`

### Testing Options

#### Option 1: Postman Request
```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "kind": "message",
      "messageId": "9f11c870-5616-49ad-b187-d93cbb100001",
      "contextId": "9f11c870-5616-49ad-b187-d93cbb100002",
      "taskId": "9f11c870-5616-49ad-b187-d93cbb100003",
      "parts": [
        {
          "kind": "text",
          "text": "Please summarize this document: The rapid advancement of artificial intelligence has transformed numerous industries..."
        }
      ]
    },
    "configuration": {
      "acceptedOutputModes": ["application/json"]
    }
  },
  "id": "9f11c870-5616-49ad-b187-d93cbb100003"
}
```

#### Option 2: PDF File Processing
```json
{
  "kind": "text",
  "text": "/path/to/your/research-paper.pdf"
}
```

#### Option 3: Raw Text Input
```json
{
  "kind": "text",
  "text": "Paste your document text here for summarization..."
}
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Client        │───▶│   Bindu Core        │───▶│   PDF Agent         │
│   (Postman)     │    │   (A2A Protocol)    │    │   (Agno + OpenRouter)│
└─────────────────┘    └─────────────────────┘    └─────────────────────┘
                              │                          │
                              ▼                          ▼
                       ┌─────────────┐         ┌─────────────────┐
                       │   DID       │         │   PDF Parser    │
                       │   Auth      │         │   Text Extract  │
                       │   Storage   │         │   Summary Gen   │
                       └─────────────┘         └─────────────────┘
```

## 📊 Output Format

The agent generates structured summaries in this format:

```markdown
# Document Summary

## Main Topic
[Identified main thesis or topic]

## Key Findings
- [Key finding 1]
- [Key finding 2]
- [Key finding 3]
- [Key finding 4]
- [Key finding 5]

## Conclusions & Recommendations
[Important conclusions or recommendations]
```

## 🔧 Configuration

### Agent Configuration
```python
config = {
    "author": "your.email@example.com",
    "name": "pdf_research_agent",
    "description": "Summarises PDF files and document text using OpenRouter.",
    "version": "1.0.0",
    "capabilities": {
        "file_processing": ["pdf"],
        "text_analysis": ["summarization", "research"],
        "streaming": False
    },
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True,
        "cors_origins": ["http://localhost:5173"],
    },
}
```

### Model Configuration
```python
agent = Agent(
    instructions=(
        "You are a research assistant that reads documents and produces clear, "
        "concise summaries. When given document text:\n"
        "  1. Identify the main topic or thesis.\n"
        "  2. List the key findings or arguments (3-5 bullet points).\n"
        "  3. Note any important conclusions or recommendations.\n"
        "Be factual and brief. If the text is too short or unclear, say so."
    ),
    model=OpenRouter(
        id="openai/gpt-4o-mini",
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
    markdown=True,
)
```

## 🌐 API Endpoints

- **Agent Endpoint**: `http://localhost:3773/`
- **Agent Card**: `http://localhost:3773/.well-known/agent.json`
- **DID Resolution**: `http://localhost:3773/did/resolve`
- **Health Check**: `http://localhost:3773/health`

## 🔍 Error Handling

The agent handles various error scenarios:

### Missing Dependencies
```
[pypdf not installed — cannot read 'file.pdf'. Run: uv add pypdf]
```

### File Not Found
```
Error reading PDF 'file.pdf': [Errno 2] No such file or directory: 'file.pdf'
```

### Empty PDF
```
PDF file 'file.pdf' appears to be empty or contains very little text.
```

### Large Documents
Documents over 50KB are automatically truncated to prevent token overflow.

## 🛡️ Security & Privacy

- **Data Privacy**: Text-only processing, no file storage
- **Content Filtering**: Educational-appropriate content filtering
- **Input Validation**: Enabled for all inputs
- **Output Sanitization**: Enabled for safe responses

## 📈 Performance

- **Response Time**: 5-15 seconds for typical documents
- **Document Size**: Supports up to 50KB of text content
- **Concurrent Requests**: Single-threaded processing
- **Memory Usage**: In-memory storage (non-persistent)

## 🧪 Testing

### Test with Sample Text
```bash
curl -X POST http://localhost:3773 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "Sample document text for testing..."}]
      }
    },
    "id": "test-1"
  }'
```

### Test with PDF File
```bash
curl -X POST http://localhost:3773 \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "message/send",
    "params": {
      "message": {
        "role": "user",
        "parts": [{"kind": "text", "text": "/path/to/test.pdf"}]
      }
    },
    "id": "test-2"
  }'
```

## 🐛 Troubleshooting

### Common Issues

#### "pypdf not installed"
```bash
uv add pypdf
```

#### "OPENROUTER_API_KEY not set"
```bash
export OPENROUTER_API_KEY="your_api_key_here"  # pragma: allowlist secret
```

#### "Port 3773 already in use"
Change the port in the configuration:
```python
"deployment": {
    "url": "http://localhost:3774",
    "expose": True,
}
```

#### "Empty PDF file"
Ensure the PDF contains extractable text, not just images.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the Bindu ecosystem. See the main repository for licensing information.

## 🙏 Acknowledgments

- **Bindu Framework**: For the microservice infrastructure
- **OpenRouter**: For AI model access
- **Agno**: For agent framework
- **pypdf**: For PDF text extraction

## 📞 Support

- **Documentation**: https://docs.getbindu.com
- **Community**: https://discord.gg/3w5zuYUuwt
- **GitHub**: https://github.com/getbindu/Bindu
- **Issues**: Report issues on the GitHub repository

---

**Built with ❤️ using Bindu Framework**
