# Vault Integration for Persistent Agent Identity

## Overview

Bindu integrates with HashiCorp Vault to provide persistent storage for DID keys and Hydra OAuth2 credentials. This is **critical for Kubernetes/pod deployments** where the filesystem is ephemeral.

## Problem Statement

Without Vault integration, when a pod dies and restarts:
- ❌ New DID keys are generated → **different agent identity**
- ❌ New Hydra OAuth client is registered → **orphaned clients in Hydra**
- ❌ Authentication breaks → **clients can't authenticate with new credentials**

## Solution

With Vault integration enabled:
- ✅ DID keys are restored from Vault → **same agent identity**
- ✅ Hydra credentials are reused → **no duplicate clients**
- ✅ Authentication persists → **seamless pod restarts**

## Architecture

### Storage Hierarchy

```
vault/
└── secret/
    └── bindu/
        ├── agents/
        │   └── {agent_id}/
        │       └── did-keys
        │           ├── private_key (PEM)
        │           ├── public_key (PEM)
        │           └── did
        └── hydra/
            └── credentials/
                └── {did}/
                    ├── client_id
                    ├── client_secret
                    ├── agent_id
                    ├── created_at
                    └── scopes
```

### Startup Flow

```
1. Pod starts
   ↓
2. Check Vault for DID keys (by agent_id)
   ↓
   ├─ Found → Restore to local filesystem
   │          └─ Use existing DID
   │
   └─ Not Found → Generate new keys
                  └─ Backup to Vault
   ↓
3. Check Vault for Hydra credentials (by DID)
   ↓
   ├─ Found → Verify client exists in Hydra
   │          ├─ Exists → Use credentials
   │          └─ Missing → Recreate client with same secret
   │
   └─ Not Found → Register new client in Hydra
                  └─ Backup credentials to Vault
   ↓
4. Agent starts with persistent identity ✅
```

## Configuration

### Environment Variables

```bash
# Enable Vault integration
VAULT__ENABLED=true

# Vault server URL
VAULT__URL=https://vault.example.com:8200
# or
VAULT_ADDR=https://vault.example.com:8200

# Vault authentication token
VAULT__TOKEN=hvs.CAESIJ...
# or
VAULT_TOKEN=hvs.CAESIJ...
```

### Example `.env` File

```bash
# Vault Configuration
VAULT__ENABLED=true
VAULT__URL=http://vault:8200
VAULT__TOKEN=your-vault-token-here

# Hydra Configuration (if using authentication)
HYDRA__ENABLED=true
HYDRA__ADMIN_URL=https://hydra-admin.getbindu.com
HYDRA__PUBLIC_URL=https://hydra.getbindu.com
HYDRA__AUTO_REGISTER_AGENTS=true
```

### Kubernetes ConfigMap/Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: bindu-vault-config
type: Opaque
stringData:
  VAULT_TOKEN: "hvs.CAESIJ..."
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: bindu-config
data:
  VAULT__ENABLED: "true"
  VAULT__URL: "http://vault.vault.svc.cluster.local:8200"
```

### Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: bindu-agent
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: agent
        image: bindu-agent:latest
        envFrom:
        - configMapRef:
            name: bindu-config
        - secretRef:
            name: bindu-vault-config
```

## Vault Setup

### 1. Enable KV Secrets Engine

```bash
vault secrets enable -path=secret kv-v2
```

### 2. Create Policy for Bindu

```hcl
# bindu-policy.hcl
path "secret/data/bindu/agents/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/bindu/agents/*" {
  capabilities = ["delete", "list"]
}

path "secret/data/bindu/hydra/*" {
  capabilities = ["create", "read", "update", "delete", "list"]
}

path "secret/metadata/bindu/hydra/*" {
  capabilities = ["delete", "list"]
}
```

```bash
vault policy write bindu bindu-policy.hcl
```

### 3. Create Token for Bindu

```bash
vault token create -policy=bindu -ttl=720h
```

### 4. (Optional) Kubernetes Auth

For production Kubernetes deployments, use Kubernetes auth instead of static tokens:

```bash
# Enable Kubernetes auth
vault auth enable kubernetes

# Configure Kubernetes auth
vault write auth/kubernetes/config \
    kubernetes_host="https://kubernetes.default.svc:443" \
    kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
    token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create role for Bindu agents
vault write auth/kubernetes/role/bindu \
    bound_service_account_names=bindu-agent \
    bound_service_account_namespaces=default \
    policies=bindu \
    ttl=24h
```

## Code Integration

### DID Setup

The DID setup automatically checks Vault:

```python
from bindu.penguin.did_setup import initialize_did_extension

# Will check Vault first if enabled
did_extension = initialize_did_extension(
    agent_id=agent_id,
    author=author,
    agent_name=agent_name,
    key_dir=key_dir,
    recreate_keys=False,  # Default: preserve existing keys
)
```

### Hydra Registration

Hydra registration checks Vault for credentials:

```python
from bindu.auth.hydra.registration import register_agent_in_hydra

# Will check Vault first if enabled
credentials = await register_agent_in_hydra(
    agent_id=str(agent_id),
    agent_name=agent_name,
    agent_url=agent_url,
    did=did_extension.did,
    credentials_dir=credentials_dir,
    did_extension=did_extension,
)
```

### Manual Vault Operations

```python
from bindu.utils.vault_client import VaultClient

vault = VaultClient()

# Store DID keys
await vault.store_did_keys(
    agent_id="agent-123",
    private_key_pem=private_key,
    public_key_pem=public_key,
    did="did:bindu:alice:my-agent"
)

# Retrieve DID keys
keys = await vault.get_did_keys("agent-123")

# Store Hydra credentials
await vault.store_hydra_credentials(credentials)

# Retrieve Hydra credentials
creds = await vault.get_hydra_credentials("did:bindu:alice:my-agent")
```

## Verification

### Check DID Persistence

```bash
# First deployment
kubectl logs bindu-agent-xxx | grep "DID extension initialized"
# Output: DID extension initialized successfully: did:bindu:alice:my-agent

# Delete pod
kubectl delete pod bindu-agent-xxx

# Check new pod
kubectl logs bindu-agent-yyy | grep "DID keys restored"
# Output: ✅ DID keys restored from Vault: did:bindu:alice:my-agent
```

### Check Hydra Credentials

```bash
# First deployment
kubectl logs bindu-agent-xxx | grep "Hydra credentials"
# Output: ✅ Hydra credentials backed up to Vault

# After pod restart
kubectl logs bindu-agent-yyy | grep "Hydra credentials"
# Output: ✅ Found Hydra credentials in Vault for DID: did:bindu:alice:my-agent
```

## Troubleshooting

### Vault Connection Issues

```bash
# Check Vault connectivity
curl -H "X-Vault-Token: $VAULT_TOKEN" $VAULT_URL/v1/sys/health

# Check Vault logs
kubectl logs -n vault vault-0
```

### Missing Credentials

```bash
# List stored DID keys
vault kv list secret/bindu/agents/

# Read specific DID keys
vault kv get secret/bindu/agents/agent-123/did-keys

# List Hydra credentials
vault kv list secret/bindu/hydra/credentials/

# Read specific credentials
vault kv get secret/bindu/hydra/credentials/did:bindu:alice:my-agent
```

### Force Regeneration

If you need to regenerate credentials:

```bash
# Delete from Vault
vault kv delete secret/bindu/agents/agent-123/did-keys
vault kv delete secret/bindu/hydra/credentials/did:bindu:alice:my-agent

# Restart pod
kubectl delete pod bindu-agent-xxx
```

## Security Best Practices

1. **Use Kubernetes Auth**: Don't use static tokens in production
2. **Rotate Tokens**: Regularly rotate Vault tokens
3. **Least Privilege**: Only grant necessary Vault permissions
4. **Audit Logs**: Enable Vault audit logging
5. **Encryption**: Use TLS for Vault communication
6. **Secret Management**: Never commit Vault tokens to git

## Migration Guide

### Migrating Existing Agents to Vault

If you have existing agents without Vault:

1. **Enable Vault** in configuration
2. **Restart agents** - they will automatically backup existing keys
3. **Verify** keys are in Vault
4. **Test** by deleting and recreating pods

### Disabling Vault

To disable Vault (not recommended for production):

```bash
VAULT__ENABLED=false
```

Agents will fall back to local filesystem storage.

## Performance Considerations

- **Startup Time**: +100-200ms for Vault lookups
- **Network**: Requires Vault connectivity
- **Caching**: Local files cached after Vault restore
- **Failover**: Falls back to local files if Vault unavailable

## References

- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [Kubernetes Auth Method](https://www.vaultproject.io/docs/auth/kubernetes)
- [KV Secrets Engine](https://www.vaultproject.io/docs/secrets/kv/kv-v2)
