"""RuntimeProvider abstraction + provider registry.

A `RuntimeProvider` controls where a bindu agent's runtime lives:

- `InProcessRuntimeProvider`: runs in the host process (today's default).
- `BoxdRuntimeProvider`: runs inside a boxd VM.

Providers are registered by string name; `bindufy()` dispatches by
``runtime.provider``. New providers (e2b, modal, ...) plug in without
core bindu changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Literal

from bindu.runtime.config import RuntimeConfig


@dataclass
class RuntimeHandle:
    """Reference to a deployed agent runtime.

    Attributes:
        name: Agent name (matches ``config["name"]``).
        url: Public URL where the agent serves (e.g.
            ``https://my-agent.boxd.sh``).
        provider: Provider id string (``"boxd"``, ``"in-process"``, ...).
        metadata: Provider-specific values (``vm_id``, ``public_ip``, ...).
            Inspectable; do not rely on shape.
    """

    name: str
    url: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)


class UnknownProviderError(LookupError):
    """Raised when ``get_provider(name)`` finds no registered provider."""


class RuntimeProvider(ABC):
    """Abstract runtime provider — subclass per backend."""

    @abstractmethod
    async def deploy(
        self,
        agent_name: str,
        source_dir: Path | None,
        config: RuntimeConfig,
        env: dict[str, str] | None = None,
        script: str | None = None,
    ) -> RuntimeHandle:
        """Deploy the agent. Returns a handle once the agent is healthy.

        ``script`` is the path to the entry-point script relative to
        ``source_dir`` (e.g. ``"agents/echo.py"``). When omitted, the
        provider may auto-detect a single top-level script — but the
        deploy CLI always passes it explicitly to avoid wrong-script
        deploys in multi-agent repos.
        """

    @abstractmethod
    async def health(self, handle: RuntimeHandle) -> bool:
        """Return True if the agent at ``handle`` is reachable & healthy."""

    @abstractmethod
    def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        """Return an async iterator of log chunks from the agent's runtime.

        Implementations are async generators (``async def`` with ``yield``);
        the method here is non-async so the signature matches what the
        generator factory returns.
        """

    @abstractmethod
    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        """Apply the user's on-exit policy when the host is shutting down."""


# ── Provider registry ──────────────────────────────────────────────

_registry: dict[str, type[RuntimeProvider]] = {}


def register_provider(name: str, cls: type[RuntimeProvider]) -> None:
    """Register a RuntimeProvider class under ``name``.

    Replaces any prior registration under the same name.
    """
    _registry[name] = cls


def get_provider(name: str) -> RuntimeProvider:
    """Instantiate the provider registered under ``name``."""
    if name not in _registry:
        raise UnknownProviderError(
            f"no runtime provider registered for {name!r}; known: {sorted(_registry)}"
        )
    return _registry[name]()
