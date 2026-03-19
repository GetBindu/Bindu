# Web Scraping AI Agent

An AI-enabled web scraping agent that crawls web pages, extracts structured data, cleans and formats outputs, and prepares datasets for analysis or integration using ScrapeGraph AI and Mem0.

## 🕷️ Features

### Core Capabilities
- **Intelligent Extraction**: Uses ScrapeGraph AI for smart, LLM-powered structured data extraction from any public web page.
- **Persistent Memory**: Integrates Mem0 for deduplication (avoiding re-scraping processed URLs) and remembering extraction profiles for specific domains.
- **Structured JSON Output**: Automatically cleans and formats extracted content into analysis-ready JSON datasets.
- **E-commerce & Content Scraping**: Optimized for product listings, blog posts, news articles, and structured tables.

### 🔧 Technical Features
- **Model**: OpenRouter's `openai/gpt-oss-120b` for advanced synthesis and formatting.
- **Tools**: 
  - `ScrapeGraphTools`: For intelligent web scraping.
  - `Mem0Tools`: For persistent memory and deduplication.
- **Environment Loading**: Automatic .env file loading for secure API key management.
- **Bindu Integration**: Fully compatible with Bindu agent framework for discovery and deployment.

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- ScrapeGraph AI API key ([Get one](https://scrapegraphai.com/))
- Mem0 API key ([Get one](https://app.mem0.ai/))
- OpenRouter API key ([Get one](https://openrouter.ai/))
- UV package manager

### Installation & Setup

1. **Navigate to Bindu root directory**:
   ```bash
   cd /path/to/bindu
   ```

2. **Install dependencies**:
   ```bash
   uv sync --extra agents
   ```

3. **Configure environment**:
   ```bash
   cp examples/web-scraping-agent/.env.example examples/web-scraping-agent/.env
   # Edit examples/web-scraping-agent/.env and add your API keys
   ```

4. **Run the agent**:
   ```bash
   uv run python examples/web-scraping-agent/web_scraping_agent.py
   ```

## 📡 Usage Examples

### Basic Extraction Queries
```python
# Direct agent usage
messages = [
    {"role": "user", "content": "Extract product listings from this e-commerce site: https://example.com/products"}
]
```

### Supported Query Types
- **E-commerce**: "Extract product names and prices from [URL]"
- **Content**: "Scrape blog titles and publish dates from [URL]"
- **General**: "Get all article headlines from this news page"
- **Structured**: "Extract the contents of the main table on [URL] into JSON"

## ️ Development

### Project Structure
```
web-scraping-agent/
├── web_scraping_agent.py    # Main agent implementation
├── .env                     # Environment variables (API keys)
├── .env.example              # Environment variables template
├── skills/                  # Skills directory
│   └── web-scraping-skill/
│       └── skill.yaml       # Skill metadata
└── README.md                # This file
```

## 🔍 Troubleshooting

### Common Issues

#### API Keys Not Found
**Error**: `SCRAPEGRAPH_API_KEY/MEM0_API_KEY/OPENROUTER_API_KEY not set`
**Solution**: Ensure your `.env` file exists in `examples/web-scraping-agent/` and contains the required keys.

#### Module Not Found
**Error**: `ModuleNotFoundError: No module named 'scrapegraphpy'` or `mem0ai`
**Solution**: Run `uv sync --extra agents` to ensure all optional dependencies are installed.

#### Scraping Fails With Credit Errors
**Error**: Messages like `insufficient credits`, `not enough credits`, or upstream `500` from ScrapeGraph.
**Solution**: Verify your ScrapeGraph account has available credits and the key is active. Then restart the agent and retry. If needed, test with a smaller target page first.

#### Agent Crashes on Startup / `ValueError` at Import
**Error**: `ValueError: API key is required` or similar from `ScrapeGraphTools` / `Mem0Tools`.
**Cause**: The agent initializes all three tools at startup. If any key is missing or set to a placeholder, the tool constructor raises immediately.
**Solution**: Ensure all three keys (`SCRAPEGRAPH_API_KEY`, `MEM0_API_KEY`, `OPENROUTER_API_KEY`) are set to real values in `examples/web-scraping-agent/.env` before running.

---

**Built with ❤️ using the Bindu Agent Framework**
