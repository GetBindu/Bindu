# Security API Reference

## Certificate Management

The `bindu.auth.certs` module provides programmatic access to certificate operations.

### CertificateManager

Manages the lifecycle of agent certificates.

```python
from bindu.auth.certs import CertificateManager

manager = CertificateManager(cert_dir=".bindu/certs/agent")

# Check if certificate is valid and renewable
is_valid = manager.ensure_certificate(
    did="did:bindu:my-agent",
    dns_names=["localhost", "my-agent.local"]
)

# Get SSL Context for client/server
ssl_context = manager.get_ssl_context()
```

### CertificateAuthority

Manages the Root CA and signing operations.

```python
from bindu.auth.certs import CertificateAuthority

ca = CertificateAuthority(ca_dir=".bindu/certs/ca")

# Revoke a certificate
ca.revoke_certificate(serial_number=123456789)

# Generate/Update CRL
ca.generate_crl()
```

## Middleware

The `bindu.server.middleware.mtls.MTLSMiddleware` enforces mTLS on all incoming requests.

- **Validation**: Checks valid signature, expiration, and revocation status.
- **Identity**: Extracts DID from Subject Common Name (CN).
- **Zero-Trust**: Rejects requests without a client certificate (401 Unauthorized).

## Settings

Security settings are configured via `bindu.settings.SecuritySettings`.

| Setting | Env Var | Default | Description |
|---------|---------|---------|-------------|
| `mtls_enabled` | `SECURITY__MTLS_ENABLED` | `false` | Enable/Disable mTLS enforcement |
| `cert_dir` | `SECURITY__CERT_DIR` | `.bindu/certs` | Directory for storing certificates |
| `auto_generate_certs` | `SECURITY__AUTO_GENERATE_CERTS` | `false` | Automatically generate CA and certs on startup |
| `ca_validity_days` | `SECURITY__CA_VALIDITY_DAYS` | `3650` | Validity period for Root CA |
| `cert_validity_days` | `SECURITY__CERT_VALIDITY_DAYS` | `365` | Validity period for Agent certs |
