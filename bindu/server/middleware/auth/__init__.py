# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Authentication middleware for Bindu.

This module provides authentication middleware implementations for
securing Bindu agents with Hydra OAuth2 authentication.

Available Providers:
- HydraMiddleware: Ory Hydra OAuth2 validation (default)
"""

from __future__ import annotations as _annotations

from .base import AuthMiddleware
from .hydra import HydraMiddleware
from .mtls import MTLSMiddleware

__all__ = [
    "AuthMiddleware",
    "HydraMiddleware",
    "MTLSMiddleware",
]
