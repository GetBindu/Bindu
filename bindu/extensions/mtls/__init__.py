# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""mTLS Extension for Bindu Agents.

Why is mTLS an Extension?
-------------------------
Like the DID extension, mTLS provides an optional capability layered on top of the
core A2A protocol. Agents that opt in fetch short-lived X.509 certificates from a
shared Smallstep step-ca server and use them to encrypt agent-to-agent traffic at
the transport layer.

This extension owns three responsibilities:

1. **Bootstrap** — at agent startup, exchange a Hydra OIDC token for an X.509
   certificate signed by the cluster's intermediate CA.
2. **Storage** — write cert/key/CA-bundle next to the DID keypair so a single
   PKI directory captures the agent's full identity, with Vault backup when
   available.
3. **Renewal** — re-fetch the certificate before expiry. Short TTL plus passive
   renewal is the revocation strategy; there is no CRL.

The CA deployment lives in ``infragrid/bindu-prod-cluster/step-ca-deploy/`` and
serves ``https://ca.getbindu.com``. See ``docs/MTLS_DEPLOYMENT_GUIDE.md`` for
the full architecture.
"""

from __future__ import annotations

from bindu.extensions.mtls.cert_store import CertStore
from bindu.extensions.mtls.mtls_agent_extension import MTLSAgentExtension
from bindu.extensions.mtls.step_ca_client import StepCAClient

__all__ = [
    "CertStore",
    "MTLSAgentExtension",
    "StepCAClient",
]
