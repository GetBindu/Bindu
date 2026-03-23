"""Hydra OAuth2 authentication module.

This module provides functionality for interacting with Ory Hydra,
including client management and agent registration.
"""

from bindu.auth.hydra.client import HydraClient
from bindu.auth.hydra.registration import (
    AgentCredentials,
    load_agent_credentials,
    register_agent_in_hydra,
    save_agent_credentials,
)

__all__ = [
    "HydraClient",
    "AgentCredentials",
    "load_agent_credentials",
    "register_agent_in_hydra",
    "save_agent_credentials",
]
