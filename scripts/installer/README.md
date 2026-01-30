# Bindu Agent Installer

Cross-platform installer scripts for Bindu AI agents.

## Files
- `install.cmd` - Windows installer
- `install.sh` - Linux/macOS installer

## Quick Start

### Windows
```cmd
install.cmd
```

### Linux/macOS
```bash
chmod +x install.sh
./install.sh
```

## Features
- Interactive configuration wizard
- Skill selection from catalog
- Multiple framework support (Agno, LangChain, CrewAI, etc.)
- Security & authentication options
- Auto-dependency installation

## Workflow
1. Run the installer
2. Enter agent name and description
3. Select skills from catalog
4. Choose framework and security options
5. Agent is created with all dependencies

## Requirements
- Git
- Python 3.8+
- Internet connection

## Troubleshooting
- Ensure Git is installed
- Run as admin on Windows if needed
- Check network connectivity 