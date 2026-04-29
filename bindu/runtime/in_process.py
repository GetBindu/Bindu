"""InProcessRuntimeProvider — runs the agent in the host process.

This provider is a deliberate no-op: it produces a ``RuntimeHandle`` pointing
at the host-local URL and lets the existing in-process server (started
elsewhere by ``bindufy()``) do the actual work. Its purpose is to make
"default behavior" inspectable through the same abstraction as boxd.
"""

from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator, Literal

from bindu.runtime.base import RuntimeHandle, RuntimeProvider, register_provider
from bindu.runtime.config import RuntimeConfig


class InProcessRuntimeProvider(RuntimeProvider):
    """Default no-op provider; the agent runs in the host process."""

    async def deploy(
        self,
        agent_name: str,
        source_dir: Path | None,
        config: RuntimeConfig,
        env: dict[str, str] | None = None,
    ) -> RuntimeHandle:
        """Return a handle pointing at the local server; nothing is deployed."""
        return RuntimeHandle(
            name=agent_name,
            url="http://localhost:3773",
            provider="in-process",
            metadata={},
        )

    async def health(self, handle: RuntimeHandle) -> bool:
        """Return True — the host process is implicitly healthy if running."""
        return True

    async def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        """Yield no log chunks — the host process logs to stdout natively."""
        if False:  # pragma: no cover
            yield b""
        return

    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        """No-op — in-process lifecycle is owned by the running server."""
        return None


register_provider("in-process", InProcessRuntimeProvider)
