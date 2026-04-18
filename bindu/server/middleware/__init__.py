# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""MIDDLEWARE MODULE EXPORTS.

This module provides middleware layers for the bindu framework including
authentication, payment protocol enforcement, and authorization receipts.

MIDDLEWARE STRUCTURE:

1. AUTHENTICATION MIDDLEWARE (auth/):
   - AuthMiddleware: Abstract base class for authentication
   - HydraMiddleware: Ory Hydra OAuth2 with hybrid DID authentication

2. PAYMENT MIDDLEWARE (x402/):
   - X402Middleware: x402 payment protocol enforcement
     Automatically handles payment verification and settlement for agents
     with execution_cost configured.

3. AUTHORIZATION MIDDLEWARE:
   - ScopeBlindMiddleware: Cedar policy enforcement with signed receipts
"""

from __future__ import annotations as _annotations

# Export authentication implementations from auth/ subdirectory
from .auth import HydraMiddleware

# Export payment middleware from x402/ subdirectory
from .x402 import X402Middleware
from .scopeblind import ScopeBlindMiddleware

# Export metrics middleware
from .metrics import MetricsMiddleware

__all__ = [
    # Authentication implementations
    "HydraMiddleware",
    # Payment middleware
    "X402Middleware",
    # Authorization middleware
    "ScopeBlindMiddleware",
    # Metrics middleware
    "MetricsMiddleware",
]
