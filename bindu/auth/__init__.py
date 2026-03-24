"""Authentication package for Bindu.

This package provides authentication clients and utilities for Ory Hydra OAuth2/OIDC.
"""

from __future__ import annotations as _annotations

# Import from new module structure
from bindu.auth.hydra.client import HydraClient
from bindu.auth.hydra.registration import (
    load_agent_credentials,
    register_agent_in_hydra,
    save_agent_credentials,
)
from bindu.common.models import AgentCredentials, OAuthClient, TokenIntrospectionResult

__all__ = [
    # Hydra
    "HydraClient",
    "TokenIntrospectionResult",
    "OAuthClient",
    # Hydra Registration
    "AgentCredentials",
    "register_agent_in_hydra",
    "load_agent_credentials",
    "save_agent_credentials",
]
