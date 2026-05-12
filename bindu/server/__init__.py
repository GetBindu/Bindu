# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""
bindu Server Module.

Unified server supporting JSON-RPC
protocols with shared task management and session contexts.
"""

from .scheduler import InMemoryScheduler
from .storage import InMemoryStorage
from .task_manager import TaskManager
from .workers import ManifestWorker

__all__ = [
    "BinduApplication",
    "InMemoryStorage",
    "InMemoryScheduler",
    "ManifestWorker",
    "TaskManager",
]


def __getattr__(name: str):
    """Lazily expose server symbols that would otherwise cause circular imports."""
    if name == "BinduApplication":
        from .applications import BinduApplication

        return BinduApplication
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
