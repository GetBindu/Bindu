# Bindu Chat UI

A modern chat interface for interacting with Bindu AI agents using the A2A (Agent-to-Agent) protocol.

## 🚀 Quickstart

```bash
npm install
npm run dev 
```

Visit `http://localhost:5173` and start chatting with your Bindu agent.

## 🏗️ Architecture

Built on SvelteKit with extensive modifications for Bindu A2A protocol support:

- **JSON-RPC 2.0**: Full protocol compliance for agent communication
- **Task State Machine**: Complete state handling (submitted → working → input-required → completed/failed)
- **Agent Discovery**: Automatic agent card discovery via `.well-known/agent.json`
- **Real-time Polling**: Background task status monitoring


## 🛠️ Development

```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run test         # Run tests
```


## 📡 API Endpoints

- `GET /api/agent-card` - Fetch agent card from `.well-known/agent.json`
- `GET /api/agent-health` - Check agent health status
- `GET /api/agent-skills` - List available agent skills
- `POST /api/did-resolve` - Resolve DID documents


---

**Built with ❤️ for the Bindu Agent Ecosystem**
