"""Mortgage agent example runner."""

import sys
import os
import io

# Force UTF-8 encoding for Windows console compatibility
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


# Add the current directory to sys.path to allow importing 'bindu'
sys.path.append(os.getcwd())

from examples.mortgage_comparison_agent.mortgage_agent import handler, config
from bindu.penguin.bindufy import bindufy

if __name__ == "__main__":
    print("Starting Mortgage Comparison Agent...")
    bindufy(config, handler)
