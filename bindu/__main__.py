"""Main entry point for the bindu CLI."""

import sys
from bindu.__version__ import get_version

def main():
    """Main CLI entry point."""
    version = get_version()
    print(f"Bindu 🌻 - The identity, communication & payments layer for AI agents")
    print(f"Version: {version}")
    print("\nAvailable Commands:")
    print("  run <agent_script.py>  Run a Bindu agent script")
    print("  --help                 Show this help message")
    print("\nTo get started, try running one of the examples:")
    print("  python examples/echo_simple_agent.py")
    print("\nFor more information, visit https://docs.getbindu.com")

if __name__ == "__main__":
    main()
