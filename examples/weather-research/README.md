# Weather Research Agent

A weather research agent that provides weather information and forecasts for any location worldwide using search-powered data retrieval.

## 🌤️ Features

### Core Capabilities
- **Real-time Weather Data**: Current conditions via web search
- **Weather Forecasts**: Multi-day forecasts for any location
- **Global Coverage**: Weather information for any city worldwide
- **Clean Response Format**: Synthesized responses without showing raw search results

### 🔧 Technical Features
- **Model**: OpenRouter's `openai/gpt-oss-120b` for advanced reasoning
- **Search Integration**: DuckDuckGo tools for real-time weather data
- **Smart Formatting**: Clean, synthesized responses
- **Environment Loading**: Automatic .env file loading
- **Bindu Integration**: Fully compatible with Bindu agent framework

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- OpenRouter API key (set in `.env` file)
- UV package manager

### Installation & Setup

1. **Navigate to Bindu root directory** (required for dependencies):
   ```bash
   cd /path/to/bindu
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment**:
   ```bash
   cp examples/weather-research/.env.example examples/weather-research/.env
   # Edit examples/weather-research/.env and add your OPENROUTER_API_KEY
   ```

4. **Run the agent**:
   ```bash
   uv run python examples/weather-research/weather_research_agent.py
   ```

## 📡 Usage Examples

### Basic Weather Queries
```python
# Direct agent usage
messages = [{"role": "user", "content": "What's the weather like in Tokyo?"}]
```

### Supported Query Types
- **Current Weather**: "weather in [location]", "current weather [location]"
- **Forecasts**: "weather forecast [location]", "5-day forecast [location]"
- **General**: "What's the weather like in [location]?"

### Response Format
The agent provides clean, synthesized weather information without showing raw search results. Example:
```
**Current Weather in Tokyo**
- Temperature: 30°F (-1°C)
- Condition: Chilly (overcast/partly cloudy)
- Note: Real-time data can shift quickly. For the most up-to-date details, check live weather services.
```

## 🔐 Configuration

### Agent Settings
```python
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "weather_research_agent",
    "description": "Research agent that finds current weather and forecasts for any city worldwide",
    "deployment": {"url": "http://localhost:3773", "expose": True}
}
```

### Model Configuration
- **Provider**: OpenRouter
- **Model**: `openai/gpt-oss-120b`
- **API Key**: Loaded from environment variable `OPENROUTER_API_KEY`

### Tools
- **DuckDuckGoTools**: For real-time weather data search

## 🛠️ Development

### Project Structure
```
weather-research/
├── weather_research_agent.py    # Main agent implementation
├── .env                     # Environment variables (API keys)
├── .env.example              # Environment variables template
├── .bindu/                  # Bindu configuration directory
├── logs/                    # Log files directory
├── skills/                  # Skills directory
│   └── weather-research-skill/
│       └── skill.yaml       # Skill metadata
└── README.md                # This file
```

### Agent Implementation
The agent uses:
- **Agno Framework**: For agent orchestration
- **OpenRouter Model**: For natural language processing
- **DuckDuckGo Search**: For real-time weather data
- **Bindu Framework**: For agent deployment and discovery

## 🔍 Troubleshooting

### Common Issues

#### API Key Not Found
**Error**: `OPENROUTER_API_KEY not set`
**Solution**:
1. Copy your OpenRouter API key
2. Add to `.env` file: `OPENROUTER_API_KEY=your_key_here`
3. Restart the agent

#### Module Not Found
**Error**: `ModuleNotFoundError: No module named 'bindu'`
**Solution**:
1. Make sure you're running from the Bindu root directory
2. Run `uv sync` to install dependencies
3. Use: `uv run python examples/weather-research/weather_research_agent.py`

#### Environment Loading Issues
**Error**: Environment variables not loading
**Solution**:
1. Ensure `.env` file exists in `examples/weather-research/` directory
2. Check that the API key is correctly formatted

## 📚 API Reference

### Endpoints
When running, the agent exposes these endpoints:
- **POST /message**: Send weather queries
- **GET /agent**: Get agent information
- **GET /health**: Health check endpoint

### Message Format
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What's the weather like in Tokyo?"
    }
  ]
}
```

## 🤝 Contributing

### Adding New Features
1. Update agent logic in `weather_research_agent.py`
2. Test thoroughly with different weather queries
3. Update documentation as needed

### Code Standards
- Follow Python PEP 8 guidelines
- Include proper error handling
- Add type hints for functions
- Document changes in README

## 📄 License

This project is part of the Bindu framework and follows the same licensing terms.

## 🆘 Support

For issues and questions:
- Check the [Bindu Documentation](https://docs.getbindu.com)
- Review existing [Issues](https://github.com/getbindu/bindu/issues)
- Join the [Community](https://discord.getbindu.com)

---

**Built with ❤️ using the Bindu Agent Framework**
