# Certificate Management Guide

This guide explains how to manage the mTLS certificate lifecycle for Bindu agents.

## Overview

Bindu uses a built-in Certificate Authority (CA) pattern for ease of use, but can also import external certificates for Mutual TLS authentication.

## Directory Structure

Certificates are stored in the configured `SECURITY__CERT_DIR` (default: `.bindu/certs`):

```
.bindu/certs/
├── ca/
│   ├── root_ca.key   # CA Private Key (Protect this!)
│   ├── root_ca.crt   # CA Public Certificate
│   ├── crl.pem       # Certificate Revocation List
│   └── revoked.txt   # List of revoked serial numbers
├── agent/
    ├── agent.key     # Agent Private Key
    └── agent.crt     # Agent Certificate (Signed by CA)
```

## Operations

### 1. Automatic Initialization
The agent automatically generates a self-signed Root CA and issues an agent certificate on first startup if `SECURITY__AUTO_GENERATE_CERTS=true`. This is suitable for development and simple deployments.

### 2. Python API for Management
You can manually trigger certificate operations using the Python API:

```python
from bindu.auth.certs import CertificateManager, CertificateAuthority
from pathlib import Path

cert_dir = Path(".bindu/certs")
ca = CertificateAuthority(cert_dir / "ca")
manager = CertificateManager(cert_dir / "agent", ca_manager=ca)

# Issue or renew certificate
manager.ensure_certificate("did:bindu:my-agent", dns_names=["my-agent.local", "localhost"])
```

### 3. Certificate Rotation
Certificates are valid for 365 days by default. The agent checks validity on startup and automatically renews if the certificate is expiring within 30 days.

To force rotation manually:
1. Delete `.bindu/certs/agent/agent.crt`.
2. Restart the agent.

### 4. Revocation
To revoke a compromised agent certificate:

```python
from bindu.auth.certs import CertificateAuthority
from pathlib import Path

ca = CertificateAuthority(Path(".bindu/certs/ca"))
# Revoke by serial number (found in the cert)
ca.revoke_certificate(123456789)
```

This updates `crl.pem`. The `MTLSMiddleware` automatically reloads this list to immediately reject revoked certificates.

### 5. Using External CA (Production)
For production environments, you likely want to use an external Trusted CA or your organization's PKI.

1. **Disable Auto-Generation**: Set `SECURITY__AUTO_GENERATE_CERTS=false`.
2. **Provision Certificates**: Place your `ca.crt`, `agent.crt`, and `agent.key` in the `SECURITY__CERT_DIR` structure.
   - `agent.crt` must be signed by the CA in `ca.crt`.
   - `agent.key` must match `agent.crt`.
3. **Trust Chain**: Ensure `ca.crt` contains the full chain if using intermediate CAs.

### 6. Client Certificates
When an agent acts as a client (calling another agent), it uses the same `agent.crt` and `agent.key` for mutual authentication. Ensure the target agent trusts your CA.
