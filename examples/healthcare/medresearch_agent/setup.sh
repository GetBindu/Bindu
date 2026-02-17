#!/bin/bash
# Setup script for MedResearch Agent
# This script automates the installation process

set -e  # Exit on error

echo "🏥 MedResearch Agent Setup"
echo "=========================="
echo ""

# Check Python version
echo "✓ Checking Python version..."
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
required_version="3.12"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Error: Python $required_version or higher is required"
    echo "   Current version: $python_version"
    echo "   Install Python 3.12+ from https://www.python.org/downloads/"
    exit 1
fi
echo "   Python $python_version detected ✓"
echo ""

# Create virtual environment
echo "✓ Creating virtual environment..."
if command -v uv &> /dev/null; then
    echo "   Using uv (faster)..."
    uv venv --python 3.12.9
else
    echo "   Using venv..."
    python3 -m venv .venv
fi
echo "   Virtual environment created ✓"
echo ""

# Activate virtual environment
echo "✓ Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source .venv/Scripts/activate
else
    # macOS/Linux
    source .venv/bin/activate
fi
echo "   Virtual environment activated ✓"
echo ""

# Install dependencies
echo "✓ Installing dependencies..."
if command -v uv &> /dev/null; then
    uv pip install -r requirements.txt
else
    pip install -r requirements.txt
fi
echo "   Dependencies installed ✓"
echo ""

# Run tests
echo "✓ Running tests to verify installation..."
pytest tests/ -v --tb=short
echo "   Tests passed ✓"
echo ""

# Display success message
echo "=========================="
echo "✨ Setup Complete!"
echo "=========================="
echo ""
echo "To start the agent:"
echo "  1. Activate the virtual environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "     .venv\\Scripts\\activate"
else
    echo "     source .venv/bin/activate"
fi
echo "  2. Run the agent:"
echo "     python medresearch_agent.py"
echo ""
echo "The agent will be available at: http://localhost:3773"
echo ""
echo "📚 Next steps:"
echo "  - Read the README.md for usage examples"
echo "  - Upload medical research papers (PDF)"
echo "  - Try multi-paper synthesis!"
echo ""
echo "Need help? Join Bindu Discord: https://discord.gg/3w5zuYUuwt"
