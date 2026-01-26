"""Authentication package for Bindu.

This package provides authentication clients and utilities for Ory Hydra and Kratos.
"""

from __future__ import annotations as _annotations

from .hydra_client import HydraClient, TokenIntrospectionResult, OAuthClient
from .kratos_client import KratosClient, OAuthToken, Identity, IdentityTraits

__all__ = [
    # Hydra
    "HydraClient",
    "TokenIntrospectionResult",
    "OAuthClient",
    # Kratos
    "KratosClient",
    "OAuthToken",
    "Identity",
    "IdentityTraits",
]
