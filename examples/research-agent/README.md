<p align="center">
  <img src="https://raw.githubusercontent.com/getbindu/create-bindu-agent/refs/heads/main/assets/light.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center">Research Agent</h1>
<h3 align="center">AI Investigative Journalism Assistant</h3>

<p align="center">
  <strong>Professional research agent combining web search with NYT-style journalism</strong><br/>
  Deep investigative research, fact-checking, and professional reporting powered by AI
</p>

<p align="center">
  <a href="https://github.com/ParasChamoli/research-agent/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/ParasChamoli/research-agent/main.yml?branch=main" alt="Build Status">
  </a>
  <a href="https://pypi.org/project/research-agent/">
    <img src="https://img.shields.io/pypi/v/research-agent" alt="PyPI Version">
  </a>
  <img src="https://img.shields.io/badge/python-3.12+-blue.svg" alt="Python Version">
  <a href="https://github.com/ParasChamoli/research-agent/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/ParasChamoli/research-agent" alt="License">
  </a>
</p>

---

## 🎯 What is Research Agent?

An AI-powered investigative journalism assistant that combines web search capabilities with professional reporting techniques. Think of it as having a New York Times researcher available 24/7.

### Key Features
*   **🔍 Web Search & Research** - Search across multiple sources using DuckDuckGo
*   **📰 Article Extraction** - Parse and analyze web articles with Newspaper4k
*   **🧠 Intelligent Analysis** - Contextual understanding and trend identification
*   **📊 Professional Reporting** - NYT-style structured reports with citations
*   **⚡ Lazy Initialization** - Fast boot times, initializes on first request
*   **🔐 Secure API Handling** - No API keys required at startup

---

## 🛠️ Tools & Capabilities

### Built-in Tools
*   **DuckDuckGoTools** - Real-time web search across multiple sources
*   **Newspaper4kTools** - Advanced article parsing and content extraction

### Research Methodology
1.  **Search Phase** - Find 10+ authoritative sources on any topic
2.  **Analysis Phase** - Cross-reference facts, identify patterns
3.  **Writing Phase** - Craft professional reports with proper structure
4.  **Quality Control** - Verify facts, ensure balanced perspectives

---

> **🌐 Join the Internet of Agents**
> Register your agent at [bindus.directory](https://bindus.directory) to make it discoverable worldwide and enable agent-to-agent collaboration. It takes 2 minutes and unlocks the full potential of your agent.

---

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/ParasChamoli/research-agent.git
cd research-agent

# Set up virtual environment with uv
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync
```

### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your API key (choose one):
# OPENAI_API_KEY=sk-...      # For OpenAI GPT-4o
# OPENROUTER_API_KEY=sk-...  # For OpenRouter (cheaper alternative)
```

### 3. Run Locally

```bash
# Start the research agent
python research_agent/main.py

# Or using uv
uv run python research_agent/main.py
```

### 4. Test with Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Access at: http://localhost:3773
```

---

## 🔧 Configuration

### Environment Variables
Create a `.env` file:

```env
# Choose ONE provider (both can be set, OpenAI takes priority)
OPENAI_API_KEY=sk-...      # OpenAI API key
OPENROUTER_API_KEY=sk-...  # OpenRouter API key (alternative)

# Optional
DEBUG=true                # Enable debug logging
```

### Port Configuration
Default port: `3773` (can be changed in `agent_config.json`)

---

## 💡 Usage Examples

### Via HTTP API

```bash
curl -X POST http://localhost:3773/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Research the impact of renewable energy policies in Germany over the last 5 years. Focus on solar and wind adoption rates, government incentives, and economic impact."
      }
    ]
  }'
```

### Sample Research Query

```text
"Investigate the latest developments in CRISPR gene editing technology.
Include recent FDA approvals, ethical considerations, and future applications
in medicine. Focus on peer-reviewed studies from the last 2 years."
```

### Expected Output Format

```markdown
# [Compelling Headline] 📰

## Executive Summary
Brief overview of key findings...

## Background & Context
Historical context and current landscape...

## Key Findings
- Main discoveries with supporting evidence
- Statistical data and expert quotes
- Comparative analysis

## Impact Analysis
Current implications and stakeholder perspectives...

## Future Outlook
Emerging trends and expert predictions...

## Sources & Methodology
List of sources analyzed and research approach...
```

---

## 🐳 Docker Deployment

### Quick Docker Setup

```bash
# Build the image
docker build -t research-agent .

# Run container
docker run -d \
  -p 3773:3773 \
  -e OPENAI_API_KEY=your_key_here \
  --name research-agent \
  research-agent

# Check logs
docker logs -f research-agent
```

### Docker Compose (Recommended)

**docker-compose.yml**
```yaml
version: '3.8'
services:
  research-agent:
    build: .
    ports:
      - "3773:3773"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    restart: unless-stopped
```

**Run with Compose:**
```bash
# Start with compose
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## 📁 Project Structure

```text
research-agent/
├── research_agent/
│   ├── __init__.py          # Package initialization
│   └── main.py              # Main agent implementation
├── agent_config.json        # Bindu agent configuration
├── pyproject.toml           # Python dependencies
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Docker Compose setup
├── README.md                # This documentation
├── .env.example             # Environment template
└── uv.lock                  # Dependency lock file
```

---

## 🔌 API Reference

### Health Check

```bash
GET http://localhost:3773/health
```
**Response:**
```json
{"status": "healthy", "agent": "Research Agent"}
```

### Chat Endpoint

```bash
POST http://localhost:3773/chat
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Your research query here"}
  ]
}
```

---

## 🧪 Testing

### Local Testing

```bash
# Install test dependencies
uv sync --group dev

# Run tests
pytest tests/

# Test with specific API key
OPENAI_API_KEY=test_key python -m pytest
```

### Integration Test

```bash
# Start agent
python research_agent/main.py &

# Test API endpoint
curl -X POST http://localhost:3773/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Test research query"}]}'
```

---

## 🚨 Troubleshooting

### Common Issues & Solutions

*   **"ModuleNotFoundError"**
    ```bash
    uv sync --force
    ```

*   **"Port 3773 already in use"**
    Change port in `agent_config.json` or kill the process:
    ```bash
    lsof -ti:3773 | xargs kill -9
    ```

*   **"No API key provided"**
    Check if `.env` exists and variable names match. Or set directly:
    ```bash
    export OPENAI_API_KEY=your_key
    ```

*   **Docker build fails**
    ```bash
    docker system prune -a
    docker-compose build --no-cache
    ```

---

## 📊 Dependencies

### Core Packages
*   `bindu` - Agent deployment framework
*   `agno` - AI agent framework
*   `openai` - OpenAI client
*   `requests` - HTTP requests
*   `rich` - Console output
*   `duckduckgo-search` - Web search
*   `newspaper4k` - Article parsing
*   `python-dotenv` - Environment management

### Development Packages
*   `pytest` - Testing framework
*   `ruff` - Code formatting/linting
*   `pre-commit` - Git hooks

---

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1.  **Fork** the repository
2.  **Create** a feature branch: `git checkout -b feature/improvement`
3.  **Make your changes** following the code style
4.  **Add tests** for new functionality
5.  **Commit** with descriptive messages
6.  **Push** to your fork
7.  **Open** a Pull Request

**Code Style:**
*   Follow PEP 8 conventions
*   Use type hints where possible
*   Add docstrings for public functions
*   Keep functions focused and small

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Credits & Acknowledgments

*   **Developer:** Paras Chamoli
*   **Framework:** [Bindu](https://bindus.directory) - Agent deployment platform
*   **Agent Framework:** [Agno](https://github.com/agno-agi/agno) - AI agent toolkit
*   **Search Tools:** DuckDuckGo Search API
*   **Content Parsing:** Newspaper4k library

### 🔗 Useful Links
*   🌐 **Bindu Directory:** [bindus.directory](https://bindus.directory)
*   📚 **Bindu Docs:** [docs.getbindu.com](https://docs.getbindu.com)
*   🐙 **GitHub:** [github.com/ParasChamoli/research-agent](https://github.com/ParasChamoli/research-agent)
*   💬 **Discord:** Bindu Community

<br>

<p align="center">
  <strong>Built with ❤️ by Paras Chamoli</strong><br/>
  <em>Transforming research with AI-powered investigative journalism</em>
</p>

<p align="center">
  <a href="https://github.com/ParasChamoli/research-agent/stargazers">⭐ Star on GitHub</a> •
  <a href="https://bindus.directory">🌐 Register on Bindu</a> •
  <a href="https://github.com/ParasChamoli/research-agent/issues">🐛 Report Issues</a>
</p>

> **Note:** This agent follows the Bindu pattern with lazy initialization and secure API key handling. It boots without API keys and only fails at runtime if keys are needed but not provided.
