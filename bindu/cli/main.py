import sys
from bindu.cli import db


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  bindu db <command>")
        sys.exit(1)

    namespace = sys.argv[1]

    if namespace == "db":
        db.handle(sys.argv[2:])
    else:
        print(f"Unknown namespace: {namespace}")
        sys.exit(1)