# Bindu Node - Production-Grade Local Development Environment

A unified, production-ready Node for the Bindu agent ecosystem. This module demonstrates clean architecture, context-aware AI integration, and advanced repository tooling.

## 🌟 Features

- **Unified Architecture**: Modular `app/` structure with separated API, Services, and Core layers
- **Context-Aware Chat**: Agent receives file content automatically during conversations
- **Advanced Tools**: Recursive TODO finder, file explorer, code summarization
- **Production Frontend**: Dark-mode 3-pane dashboard with live code viewing
- **Type-Safe Config**: Pydantic-based environment validation

## 🚀 Quick Start

```bash
cd bindu_node
pip install -r ../requirements.txt
python main.py
```

Visit: **http://localhost:8000**

## 📁 Structure

```
bindu_node/
├── app/
│   ├── api/       # FastAPI endpoints
│   ├── core/      # Config & utilities
│   ├── services/  # Agent & Repo logic
│   └── static/    # Frontend assets
└── main.py        # Entry point
```
