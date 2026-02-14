# Security Best Practices for Bindu Agents

This guide outlines the security best practices for deploying and managing Bindu agents in a production environment.

## Zero-Trust Architecture

Bindu employs a Zero-Trust architecture where no entity is trusted by default, regardless of network location.

### 1. Mutual TLS (mTLS)
- **Always Enable mTLS**: Ensure `SECURITY__MTLS_ENABLED=true` is set in production.
- **Strict Validation**: The server enforces `ssl.CERT_REQUIRED`, rejecting any connection without a valid client certificate with a trusted root.
- **Identity Verification**: The system validates that the Certificate's Common Name (CN) matches the agent's DID.
- **Root CA Protection**: Keep your Root CA private key offline or in a secure Vault. Do not store it on edge nodes.

### 2. Network Segmentation
- Isolate agent networks.
- Use firewalls to restrict access to agent ports (default: 3773) only to known peers or the load balancer.
- Bindu's internal certificate validation allows it to run safely even on flat networks, but segmentation adds defense-in-depth.

### 3. Identity and DIDs
- Bindu uses Decentralized Identifiers (DIDs) as the primary identity mechanism.
- Ensure DIDs are resolved from a trusted registry or use `did:key` for self-certifying trust.
- Map DIDs to Certificates using the Common Name (CN) field.

## Secure Configuration

### 1. Environment Variables
- Never commit `.env` files to version control.
- Use a secrets manager (like HashiCorp Vault, AWS Secrets Manager) to inject sensitive environment variables at runtime.

### 2. Least Privilege
- Run the agent process as a non-root user.
- Limit filesystem access to only the necessary directories (`.bindu/certs`, `.bindu/storage`).

### 3. TLS Hardening
- **TLS 1.3**: Bindu enforces TLS 1.2 or higher. We recommend TLS 1.3 for maximum security.
- **Cipher Suites**: Use strong, modern cipher suites. Avoid deprecated ciphers like RC4, 3DES, or CBC mode suites.
- **HSTS**: If exposing via HTTPS directly, ensure HTTP Strict Transport Security (HSTS) is enabled.

## Monitoring and Auditing

- **Enable Audit Logs**: Monitor access logs for 401 Unauthorized attempts, which may indicate unauthorized access attempts or misconfigured peers.
- **Certificate Expiry Monitoring**: Set up alerts for certificates expiring within 30 days. Bindu logs warnings for expiring certs.
- **Revocation Lists**: Regularly update the Certificate Revocation List (CRL) if using manual revocation.

## Updates and Patching

- Regularly update the Bindu library to the latest version to apply security patches.
- Keep the underlying Python environment and OS patched.
