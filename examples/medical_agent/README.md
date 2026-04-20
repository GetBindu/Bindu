# Medical Research Agent

A medical research agent that provides health information, symptom analysis, and wellness guidance using search-powered medical data retrieval.

## :hospital: Features

### Core Capabilities
- **Medical Information**: General health and wellness information
- **Symptom Analysis**: Preliminary symptom assessment and guidance
- **Drug Information**: Medication details and interactions
- **Wellness Advice**: General health and lifestyle recommendations
- **Medical Research**: Search-powered medical data and studies
- **Clean Response Format**: Synthesized responses with proper medical disclaimers

### :gear: Technical Features
- **Model**: OpenRouter's `google/gemini-2.0-flash-001` for advanced medical reasoning
- **Search Integration**: DuckDuckGo tools for real-time medical information
- **Smart Formatting**: Clean, synthesized responses with medical disclaimers
- **Environment Loading**: Automatic .env file loading
- **Bindu Integration**: Fully compatible with Bindu agent framework

## :rocket: Quick Start

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
   cp examples/medical_agent/.env.example examples/medical_agent/.env
   # Edit examples/medical_agent/.env and add your OPENROUTER_API_KEY
   ```

4. **Run the agent**:
   ```bash
   uv run python examples/medical_agent/medical_agent.py
   ```

## :satellite: Usage Examples

### Basic Medical Queries
```python
# Direct agent usage
messages = [{"role": "user", "content": "What are the symptoms of flu?"}]
```

### Supported Query Types
- **Symptom Analysis**: "symptoms of [condition]", "what causes [symptom]"
- **Medication Info**: "information about [drug]", "side effects of [medication]"
- **Health Guidance**: "how to prevent [condition]", "tips for [health goal]"
- **Wellness**: "benefits of [exercise/diet]", "healthy lifestyle tips"

### Response Format
The agent provides clean, synthesized medical information with appropriate disclaimers. Example:
```
**Flu Symptoms Overview**
- Common symptoms: Fever, cough, sore throat, body aches
- Less common: Headache, fatigue, vomiting, diarrhea
- **Important**: This information is for educational purposes only. Always consult a healthcare professional for medical advice, diagnosis, or treatment.
```

## :key: Configuration

### Agent Settings
```python
config = {
    "author": "bindu.builder@getbindu.com",
    "name": "medical_agent",
    "description": "Medical research agent that provides health information and symptom analysis",
    "deployment": {"url": "http://localhost:3773", "expose": True}
}
```

### Model Configuration
- **Provider**: OpenRouter
- **Model**: `google/gemini-2.0-flash-001`
- **API Key**: Loaded from environment variable `OPENROUTER_API_KEY`

### Tools
- **DuckDuckGoTools**: For real-time medical information search

## :wrench: Development

### Project Structure
```
medical_agent/
|   medical_agent.py           # Main agent implementation
|   .env                      # Environment variables (API keys)
|   .env.example              # Environment variables template
|   .bindu/                  # Bindu configuration directory
|   logs/                     # Log files directory
|   skills/                   # Skills directory
|   |   medical-research-skill/
|   |       |   skill.yaml   # Skill metadata
|   |       |   README.md    # Skill documentation
|   README.md                 # This file
```

### Agent Implementation
The agent uses:
- **Agno Framework**: For agent orchestration
- **OpenRouter Model**: For natural language processing
- **DuckDuckGo Search**: For real-time medical information
- **Bindu Framework**: For agent deployment and discovery

## :mag: Troubleshooting

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
3. Use: `uv run python examples/medical_agent/medical_agent.py`

#### Environment Loading Issues
**Error**: Environment variables not loading
**Solution**:
1. Ensure `.env` file exists in `examples/medical_agent/` directory
2. Check that the API key is correctly formatted

## :books: API Reference

### Endpoints
When running, the agent exposes these endpoints:
- **POST /message**: Send medical queries
- **GET /agent**: Get agent information
- **GET /health**: Health check endpoint

### Message Format
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What are the symptoms of flu?"
    }
  ]
}
```

## :handshake: Contributing

### Adding New Features
1. Update agent logic in `medical_agent.py`
2. Test thoroughly with different medical queries
3. Update documentation as needed

### Code Standards
- Follow Python PEP 8 guidelines
- Include proper error handling
- Add type hints for functions
- Document changes in README

## :page_facing_up: License

This project is part of the Bindu framework and follows the same licensing terms.

## :sos: Support

For issues and questions:
- Check the [Bindu Documentation](https://docs.getbindu.com)
- Review existing [Issues](https://github.com/getbindu/bindu/issues)
- Join the [Community](https://discord.getbindu.com)

---

**Built with :heart: using the Bindu Agent Framework**

## :warning: Medical Disclaimer

This agent provides general health information for educational purposes only and is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of qualified healthcare providers with any questions you may have regarding a medical condition.
