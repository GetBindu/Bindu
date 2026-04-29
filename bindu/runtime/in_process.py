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
    async def deploy(
        self,
        agent_name: str,
        source_dir: Path | None,
        config: RuntimeConfig,
        env: dict[str, str] | None = None,
    ) -> RuntimeHandle:
        return RuntimeHandle(
            name=agent_name,
            url="http://localhost:3773",
            provider="in-process",
            metadata={},
        )

    async def health(self, handle: RuntimeHandle) -> bool:
        return True

    async def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        # No log stream from a no-op provider; yield nothing.
        if False:  # pragma: no cover
            yield b""
        return

    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        # In-process lifecycle is owned by the existing server; nothing to do.
        return None


register_provider("in-process", InProcessRuntimeProvider)
