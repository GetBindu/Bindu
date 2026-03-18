from pathlib import Path
from alembic import command
from alembic.config import Config
import sys


def get_alembic_config() -> Config:
    framework_root = Path(__file__).resolve().parent.parent.parent
    alembic_dir = framework_root / "alembic"

    cfg = Config()

    # Absolute script location (critical)
    cfg.set_main_option("script_location", str(alembic_dir))

    # Optional but safe: make version path explicit
    cfg.set_main_option(
        "version_locations",
        str(alembic_dir / "versions")
    )

    return cfg


def handle(args):
    if not args:
        print("Usage:")
        print("  bindu db upgrade [revision]")
        print("  bindu db downgrade [revision]")
        print("  bindu db revision -m 'message'")
        print("  bindu db revision --autogenerate -m 'message'")
        print("  bindu db current")
        print("  bindu db history")
        sys.exit(1)

    cfg = get_alembic_config()
    cmd = args[0]

    if cmd == "upgrade":
        revision = args[1] if len(args) > 1 else "head"
        print(f"Upgrading database to revision: {revision}")
        command.upgrade(cfg, revision)
        print("Upgrade complete.")

    elif cmd == "downgrade":
        revision = args[1] if len(args) > 1 else "-1"
        print(f"Downgrading database to revision: {revision}")
        command.downgrade(cfg, revision)
        print("Downgrade complete.")

    elif cmd == "revision":
        autogen = "--autogenerate" in args

        if "-m" not in args:
            print("Error: revision requires -m 'message'")
            sys.exit(1)

        msg_index = args.index("-m") + 1
        if msg_index >= len(args):
            print("Error: missing revision message")
            sys.exit(1)

        message = args[msg_index]

        if autogen:
            print(f"Creating new revision (autogenerate): '{message}'")
        else:
            print(f"Creating new revision: '{message}'")

        command.revision(cfg, message=message, autogenerate=autogen)
        print("Revision created.")

    elif cmd == "current":
        print("Current database revision:")
        command.current(cfg)

    elif cmd == "history":
        print("Migration history:")
        command.history(cfg)

    else:
        print(f"Unknown db command: {cmd}")
        sys.exit(1)