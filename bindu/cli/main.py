import sys


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  bindu db <command>")
        print("  bindu train [options]")
        print("  bindu canary [options]")
        sys.exit(1)

    namespace = sys.argv[1]

    if namespace == "db":
        # Lazy import to avoid loading db dependencies when not needed
        from bindu.cli import db
        db.handle(sys.argv[2:])
    elif namespace == "train":
        # Lazy import to avoid loading dspy dependencies when not needed
        from bindu.cli import train
        # Adjust sys.argv so argparse in train.main() works correctly
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        train.main()
    elif namespace == "canary":
        # Lazy import to avoid loading dspy dependencies when not needed
        from bindu.cli import canary
        # Adjust sys.argv so argparse in canary.main() works correctly
        sys.argv = [sys.argv[0]] + sys.argv[2:]
        canary.main()
    else:
        print(f"Unknown namespace: {namespace}")
        sys.exit(1)