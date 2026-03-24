"""Thread-safe agent registry for gRPC-registered remote agents.

Tracks agents that have registered via the BinduService.RegisterAgent RPC.
Each entry maps an agent_id to its gRPC callback address, manifest, and
lifecycle timestamps.

Thread safety is required because the gRPC server uses a ThreadPoolExecutor
for handling concurrent RegisterAgent/Heartbeat/UnregisterAgent calls.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from bindu.utils.logging import get_logger

if TYPE_CHECKING:
    from bindu.common.models import AgentManifest

logger = get_logger("bindu.grpc.registry")


@dataclass
class RegisteredAgent:
    """A remote agent registered via gRPC.

    Attributes:
        agent_id: UUID string of the registered agent.
        grpc_callback_address: The SDK's AgentHandler gRPC address
            (e.g., "localhost:50052"). Core calls HandleMessages here.
        manifest: The AgentManifest created during registration.
        registered_at: UTC timestamp when the agent was registered.
        last_heartbeat: UTC timestamp of the last heartbeat received.
    """

    agent_id: str
    grpc_callback_address: str
    manifest: AgentManifest
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AgentRegistry:
    """Thread-safe in-memory registry for gRPC-registered agents.

    Provides register/unregister/lookup operations protected by a
    threading.Lock, since the gRPC server's ThreadPoolExecutor may
    call these concurrently.
    """

    def __init__(self) -> None:  # noqa: D107
        self._agents: dict[str, RegisteredAgent] = {}
        self._lock = threading.Lock()

    def register(
        self,
        agent_id: str,
        grpc_callback_address: str,
        manifest: AgentManifest,
    ) -> RegisteredAgent:
        """Register a new remote agent.

        Args:
            agent_id: UUID string of the agent.
            grpc_callback_address: SDK's AgentHandler gRPC address.
            manifest: AgentManifest created during registration.

        Returns:
            The RegisteredAgent entry.
        """
        entry = RegisteredAgent(
            agent_id=agent_id,
            grpc_callback_address=grpc_callback_address,
            manifest=manifest,
        )
        with self._lock:
            self._agents[agent_id] = entry
        logger.info(
            f"Registered agent {agent_id} with callback at {grpc_callback_address}"
        )
        return entry

    def get(self, agent_id: str) -> RegisteredAgent | None:
        """Look up a registered agent by ID.

        Args:
            agent_id: UUID string of the agent.

        Returns:
            RegisteredAgent if found, None otherwise.
        """
        with self._lock:
            return self._agents.get(agent_id)

    def unregister(self, agent_id: str) -> bool:
        """Remove an agent from the registry.

        Args:
            agent_id: UUID string of the agent to remove.

        Returns:
            True if the agent was found and removed, False otherwise.
        """
        with self._lock:
            removed = self._agents.pop(agent_id, None)
        if removed:
            logger.info(f"Unregistered agent {agent_id}")
            return True
        logger.warning(f"Attempted to unregister unknown agent {agent_id}")
        return False

    def update_heartbeat(self, agent_id: str) -> bool:
        """Update the last heartbeat timestamp for an agent.

        Args:
            agent_id: UUID string of the agent.

        Returns:
            True if the agent was found and updated, False otherwise.
        """
        with self._lock:
            entry = self._agents.get(agent_id)
            if entry:
                entry.last_heartbeat = datetime.now(timezone.utc)
                return True
        return False

    def list_agents(self) -> list[RegisteredAgent]:
        """Return a snapshot of all registered agents.

        Returns:
            List of RegisteredAgent entries (copy, safe to iterate).
        """
        with self._lock:
            return list(self._agents.values())

    def __len__(self) -> int:  # noqa: D105
        with self._lock:
            return len(self._agents)
