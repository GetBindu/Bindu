<p align="center">
  <img src="https://raw.githubusercontent.com/getbindu/create-bindu-agent/refs/heads/main/assets/light.svg" alt="bindu Logo" width="200">
</p>

<h1 align="center">multilingual-collab-agent-v2</h1>

<p align="center">
  <strong>Identity-aware multilingual research and collaboration agent built on Bindu</strong>
</p>

<p align="center">
  <a href="https://github.com/Subhajitdas99/multilingual-collab-agent-v2/actions/workflows/main.yml?query=branch%3Amain">
    <img src="https://img.shields.io/github/actions/workflow/status/Subhajitdas99/multilingual-collab-agent-v2/main.yml?branch=main" alt="Build status">
  </a>
  <a href="https://img.shields.io/github/license/Subhajitdas99/multilingual-collab-agent-v2">
    <img src="https://img.shields.io/github/license/Subhajitdas99/multilingual-collab-agent-v2" alt="License">
  </a>
</p>

---

## 📖 Overview

Identity-aware multilingual research and collaboration agent built on Bindu. Built on the [Bindu Agent Framework](https://github.com/getbindu/bindu) for the Internet of Agents.

**Key Capabilities:**
- 🔍 [Add your key capabilities here]
- ✅ [Add another capability]
- 🚨 [Add another capability]

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- API keys for OpenRouter and Mem0 (both have free tiers)

### Installation

```bash
# Clone the repository
git clone https://github.com/Subhajitdas99/multilingual-collab-agent-v2.git
cd multilingual-collab-agent-v2

# Create virtual environment
uv venv --python 3.12.9
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Configure environment
cp .env.example .env
```

### Configuration

Edit `.env` and add your API keys:

| Key | Get It From | Required |
|-----|-------------|----------|
| `OPENROUTER_API_KEY` | [OpenRouter](https://openrouter.ai/keys) | ✅ Yes |
| `MEM0_API_KEY` | [Mem0 Dashboard](https://app.mem0.ai/dashboard/api-keys) | If you want to use Mem0 tools |

### Run the Agent

```bash
# Start the agent
uv run python -m multilingual_collab_agent_v2

# Agent will be available at http://localhost:3773
```

### Github Setup

```bash
# Initialize git repository and commit your code
git init -b main
git add .
git commit -m "Initial commit"

# Create repository on GitHub and push (replace with your GitHub username)
gh repo create Subhajitdas99/multilingual-collab-agent-v2 --public --source=. --remote=origin --push
```

---

## 💡 Usage

### Example Queries

```bash
# Example query 1
"[Add example query here]"

# Example query 2
"[Add another example]"
```

### Input Formats

**Plain Text:**
```
[Describe expected input format]
```

**JSON:**
```json
{
  "content": "[example content]",
  "focus": "[example focus]"
}
```

### Output Structure

The agent returns structured output with:
- **[Output Component 1]**: Description
- **[Output Component 2]**: Description
- **[Output Component 3]**: Description

---

## 🔌 API Usage

The agent exposes a RESTful API when running. Default endpoint: `http://localhost:3773` 

### Quick Start

For complete API documentation, request/response formats, and examples, visit:

📚 **[Bindu API Reference - Send Message to Agent](https://docs.getbindu.com/api-reference/all-the-tasks/send-message-to-agent)**


### Additional Resources

- 📖 [Full API Documentation](https://docs.getbindu.com/api-reference/all-the-tasks/send-message-to-agent)
- 📦 [Postman Collections](https://github.com/GetBindu/Bindu/tree/main/postman/collections)
- 🔧 [API Reference](https://docs.getbindu.com)

---

## 🎯 Skills

### multilingual_collab_agent_v2 (v1.0.0)

**Primary Capability:**
- [Describe what this skill does]
- [Add key features]

**Features:**
- [Feature 1]
- [Feature 2]
- [Feature 3]

**Best Used For:**
- [Use case 1]
- [Use case 2]
- [Use case 3]

**Not Suitable For:**
- [Anti-pattern 1]
- [Anti-pattern 2]

**Performance:**
- Average processing time: ~[X] seconds
- Max concurrent requests: [N]
- Memory per request: [X]MB

---

## 🐳 Docker Deployment

### Local Docker Setup

```bash
# Build and run with Docker Compose
docker-compose up --build

# Agent will be available at http://localhost:3773
```

### Docker Configuration

The agent runs on port `3773` and requires:
- `OPENROUTER_API_KEY` environment variable
- `MEM0_API_KEY` environment variable

Configure these in your `.env` file before running.

### Production Deployment

```bash
# Use production compose file
docker-compose -f docker-compose.prod.yml up -d
```

---

## 🌐 Deploy to bindus.directory

Make your agent discoverable worldwide and enable agent-to-agent collaboration.

### Setup GitHub Secrets

```bash
# Authenticate with GitHub
gh auth login

# Set deployment secrets
gh secret set BINDU_API_TOKEN --body "<your-bindu-api-key>"
gh secret set DOCKERHUB_TOKEN --body "<your-dockerhub-token>"
```

Get your keys:
- **Bindu API Key**: [bindus.directory](https://bindus.directory) dashboard
- **Docker Hub Token**: [Docker Hub Security Settings](https://hub.docker.com/settings/security)

### Deploy

```bash
# Push to trigger automatic deployment
git push origin main
```

GitHub Actions will automatically:
1. Build your agent
2. Create Docker container
3. Push to Docker Hub
4. Register on bindus.directory

---

## 🛠️ Development

### Project Structure

```
multilingual-collab-agent-v2/
├── multilingual_collab_agent_v2/
│   ├── skills/
│   │   └── multilingual_collab_agent_v2/
│   │       ├── skill.yaml          # Skill configuration
│   │       └── __init__.py
│   ├── __init__.py
│   ├── __main__.py
│   ├── main.py                     # Agent entry point
│   └── agent_config.json           # Agent configuration
├── tests/
│   └── test_main.py
├── .env.example
├── docker-compose.yml
├── Dockerfile.agent
└── pyproject.toml
```

### Running Tests

```bash
make test              # Run all tests
make test-cov          # With coverage report
```

### Code Quality

```bash
make format            # Format code with ruff
make lint              # Run linters
make check             # Format + lint + test
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run manually
uv run pre-commit run -a
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature` 
3. Commit your changes: `git commit -m 'Add amazing feature'` 
4. Push to the branch: `git push origin feature/amazing-feature` 
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Powered by Bindu

Built with the [Bindu Agent Framework](https://github.com/getbindu/bindu)

**Why Bindu?**
- 🌐 **Internet of Agents**: A2A, AP2, X402 protocols for agent collaboration
- ⚡ **Zero-config setup**: From idea to production in minutes
- 🛠️ **Production-ready**: Built-in deployment, monitoring, and scaling

**Build Your Own Agent:**
```bash
uvx cookiecutter https://github.com/getbindu/create-bindu-agent.git
```

---

## 📚 Resources

- 📖 [Full Documentation](https://Subhajitdas99.github.io/multilingual-collab-agent-v2/)
- 💻 [GitHub Repository](https://github.com/Subhajitdas99/multilingual-collab-agent-v2/)
- 🐛 [Report Issues](https://github.com/Subhajitdas99/multilingual-collab-agent-v2/issues)
- 💬 [Join Discord](https://discord.gg/3w5zuYUuwt)
- 🌐 [Agent Directory](https://bindus.directory)
- 📚 [Bindu Documentation](https://docs.getbindu.com)

---

<p align="center">
  <strong>Built with 💛 by the team from Amsterdam 🌷</strong>
</p>

<p align="center">
  <a href="https://github.com/Subhajitdas99/multilingual-collab-agent-v2">⭐ Star this repo</a> •
  <a href="https://discord.gg/3w5zuYUuwt">💬 Join Discord</a> •
  <a href="https://bindus.directory">🌐 Agent Directory</a>
</p>

