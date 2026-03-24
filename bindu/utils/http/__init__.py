"""HTTP client utilities for Bindu.

This package provides HTTP clients for various purposes:
- Generic async HTTP client with retry logic
- Hybrid authentication client (OAuth2 + DID signatures)
- Vault client for secrets management
- Token utilities for OAuth operations
"""

from .auth_client import HybridAuthClient
from .client import AsyncHTTPClient, http_client
from .tokens import (
    get_client_credentials_token,
    introspect_token,
    revoke_token,
)
from .vault_client import (
    VaultClient,
    backup_did_keys_to_vault,
    restore_did_keys_from_vault,
)

__all__ = [
    # HTTP Client
    "AsyncHTTPClient",
    "http_client",
    # Hybrid Auth Client
    "HybridAuthClient",
    # Vault Client
    "VaultClient",
    "restore_did_keys_from_vault",
    "backup_did_keys_to_vault",
    # Token utilities
    "get_client_credentials_token",
    "introspect_token",
    "revoke_token",
]
