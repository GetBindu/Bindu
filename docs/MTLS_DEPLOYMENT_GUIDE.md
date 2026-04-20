# mTLS Deployment Guide for DevOps

> **Audience:** DevOps/Infrastructure team deploying Smallstep step-ca on Infragrid cluster
> **Goal:** Enable mutual TLS (mTLS) for all Bindu agent-to-agent and core-to-SDK communication
> **Timeline:** Deploy step-ca alongside existing Hydra OAuth2 server

---

## Table of Contents

1. [Context: Why mTLS](#1-context-why-mtls)
2. [Architecture Overview](#2-architecture-overview)
3. [Current Infrastructure State](#3-current-infrastructure-state)
4. [What We're Adding](#4-what-were-adding)
5. [step-ca Deployment](#5-step-ca-deployment)
6. [OIDC Provisioner Configuration](#6-oidc-provisioner-configuration)
7. [Root CA and Key Management](#7-root-ca-and-key-management)
8. [Certificate Lifecycle](#8-certificate-lifecycle)
9. [DNS and Networking](#9-dns-and-networking)
10. [Monitoring and Alerting](#10-monitoring-and-alerting)
11. [Disaster Recovery](#11-disaster-recovery)
12. [Security Hardening](#12-security-hardening)
13. [Rollout Plan](#13-rollout-plan)
14. [Verification Checklist](#14-verification-checklist)

---

## 1. Context: Why mTLS

Bindu is a distributed agent framework. Agents communicate over HTTP (A2A protocol on port 3773) and gRPC (core-to-SDK on port 3774). Today, these channels rely on application-level security (OAuth2 tokens + DID signatures) but the transport itself is not encrypted or mutually authenticated.

**What mTLS adds:**
- Encrypted transport between all agents (AES-256 via TLS 1.3)
- Mutual authentication — both sides present certificates and verify each other
- Man-in-the-middle prevention — attacker cannot forge certificates
- Passive revocation — short-lived certificates (24h) expire without needing CRL/OCSP

**mTLS does NOT replace existing security.** It adds a transport layer underneath:

```
Layer 3: DID Signature       (message integrity)     — existing
Layer 2: OAuth2 Token        (authorization)          — existing, via Hydra
Layer 1: mTLS Certificate    (transport encryption)   — NEW, via step-ca
```

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Infragrid Cluster                           │
│                                                                  │
│  ┌──────────────────┐     ┌──────────────────┐                  │
│  │  Ory Hydra        │     │  Smallstep step-ca │                │
│  │  (existing)       │     │  (NEW)             │                │
│  │                   │     │                    │                │
│  │  Admin  :4445     │     │  CA API   :9000    │                │
│  │  Public :4444     │     │  ACME     :9000    │                │
│  │                   │     │                    │                │
│  │  Issues:          │     │  Issues:           │                │
│  │  - OAuth2 tokens  │────►│  - X.509 certs     │                │
│  │  - OIDC tokens    │     │  (validates Hydra   │                │
│  │                   │     │   OIDC tokens)      │                │
│  └──────────────────┘     └──────────────────┘                  │
│                                                                  │
│  ┌──────────────────┐                                           │
│  │  HashiCorp Vault  │                                          │
│  │  (existing)       │                                          │
│  │                   │                                          │
│  │  Stores:          │                                          │
│  │  - Root CA key    │                                          │
│  │  - DID keys       │                                          │
│  │  - Hydra creds    │                                          │
│  └──────────────────┘                                           │
└─────────────────────────────────────────────────────────────────┘

           │                    │
           │ OIDC token         │ Certificate request
           │                    │ (with OIDC token as proof)
           ▼                    ▼

┌─────────────────────────────────────────────────────────────────┐
│                      Agent Network                               │
│                                                                  │
│  Agent A ◄════ mTLS (encrypted, mutual auth) ════► Agent B     │
│  :3773                                               :3773      │
│                                                                  │
│  Core   ◄════ mTLS (encrypted, mutual auth) ════► SDK (TS/KT) │
│  :3774                                               :50052     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Current Infrastructure State

Before starting, confirm these services are running on Infragrid:

| Service | URL | Port | Status |
|---------|-----|------|--------|
| Ory Hydra Admin | `https://hydra-admin.getbindu.com` | 4445 | Must be running |
| Ory Hydra Public | `https://hydra.getbindu.com` | 4444 | Must be running |
| HashiCorp Vault | `https://vault.getbindu.com` | 8200 | Must be running |
| Hydra OIDC Discovery | `https://hydra.getbindu.com/.well-known/openid-configuration` | 4444 | Must return valid JSON |
| Hydra JWKS | `https://hydra.getbindu.com/.well-known/jwks.json` | 4444 | Must return valid JWKS |

**Verification commands:**

```bash
# Check Hydra OIDC discovery
curl -s https://hydra.getbindu.com/.well-known/openid-configuration | jq .issuer

# Check Hydra JWKS
curl -s https://hydra.getbindu.com/.well-known/jwks.json | jq '.keys | length'

# Check Vault is accessible
vault status
```

---

## 4. What We're Adding

| Component | What | Where | Port |
|-----------|------|-------|------|
| **step-ca** | Private Certificate Authority | Infragrid cluster (new pod) | 9000 |
| **Root CA certificate** | Trust anchor for all agents | Vault (stored), step-ca (referenced) | N/A |
| **Intermediate CA** | Online issuing CA | step-ca pod | N/A |
| **OIDC provisioner** | Validates Hydra tokens for cert issuance | step-ca config | N/A |
| **DNS record** | `step-ca.getbindu.com` | Cluster DNS / external DNS | N/A |

**No changes to Hydra.** step-ca is a consumer of Hydra's OIDC tokens, not a modification to Hydra.

---

## 5. step-ca Deployment

### 5.1 Prerequisites

```bash
# Add Smallstep Helm repository
helm repo add smallstep https://smallstep.github.io/helm-charts
helm repo update
```

### 5.2 Generate Root CA (one-time, offline)

**This is the most critical step. The root CA key must be generated offline and stored securely in Vault. It should NEVER exist on the step-ca pod.**

```bash
# On a secure offline machine (not on the cluster)

# Install step CLI
brew install step

# Generate root CA key pair
step certificate create \
  "Bindu Root CA" \
  root_ca.crt root_ca.key \
  --profile root-ca \
  --kty EC \
  --curve P-256 \
  --not-after 87600h  # 10 years

# Verify the root certificate
step certificate inspect root_ca.crt
```

**Expected output:**

```
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: <random>
    Signature Algorithm: ECDSA-SHA256
        Issuer: CN=Bindu Root CA
        Validity
            Not Before: 2026-03-24 ...
            Not After : 2036-03-24 ...
        Subject: CN=Bindu Root CA
        Subject Public Key Info:
            Public Key Algorithm: ECDSA
                Public-Key: (256 bit)
```

### 5.3 Store Root CA Key in Vault

```bash
# Store root CA private key in Vault (NEVER on the cluster)
vault kv put secret/bindu/step-ca/root-ca \
  certificate=@root_ca.crt \
  private_key=@root_ca.key

# Verify it's stored
vault kv get secret/bindu/step-ca/root-ca

# DELETE the root CA key from the local machine
shred -u root_ca.key  # Linux
# or
rm -P root_ca.key     # macOS
```

**The root CA certificate (root_ca.crt) is public — keep a copy. The root CA key (root_ca.key) must ONLY exist in Vault.**

### 5.4 Generate Intermediate CA

```bash
# Generate intermediate CA key pair (this will run on step-ca)
step certificate create \
  "Bindu Intermediate CA" \
  intermediate_ca.crt intermediate_ca.key \
  --profile intermediate-ca \
  --ca root_ca.crt \
  --ca-key root_ca.key \
  --kty EC \
  --curve P-256 \
  --not-after 43800h  # 5 years
```

### 5.5 Create Kubernetes Secrets

```bash
# Create namespace
kubectl create namespace bindu-ca

# Store intermediate CA cert and key as K8s secrets
kubectl create secret tls step-ca-intermediate \
  --cert=intermediate_ca.crt \
  --key=intermediate_ca.key \
  --namespace=bindu-ca

# Store root CA certificate (public, used for verification)
kubectl create secret generic step-ca-root \
  --from-file=root_ca.crt=root_ca.crt \
  --namespace=bindu-ca

# Store step-ca password (used to encrypt the intermediate key at rest)
STEP_CA_PASSWORD=$(openssl rand -base64 32)
kubectl create secret generic step-ca-password \
  --from-literal=password=$STEP_CA_PASSWORD \
  --namespace=bindu-ca
```

### 5.6 Helm Values File

Create `step-ca-values.yaml`:

```yaml
# step-ca-values.yaml
# Helm values for Smallstep step-ca deployment on Infragrid

# Pod configuration
replicaCount: 2  # HA: run 2 replicas behind a service

image:
  repository: cr.step.sm/smallstep/step-ca
  tag: "0.27.5"  # Pin to specific version
  pullPolicy: IfNotPresent

# Service configuration
service:
  type: ClusterIP
  port: 9000
  targetPort: 9000

# Resource limits
resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"

# Persistence for CA database
persistence:
  enabled: true
  storageClass: "standard"  # Adjust to your cluster's storage class
  size: 1Gi

# Inject existing secrets
existingSecrets:
  ca:
    name: step-ca-intermediate
  root:
    name: step-ca-root
  password:
    name: step-ca-password

# step-ca configuration (ca.json)
# This is the core configuration — see Section 6 for details
inject:
  enabled: true
  config:
    files:
      ca.json:
        root: /home/step/certs/root_ca.crt
        federatedRoots: []
        crt: /home/step/certs/intermediate_ca.crt
        key: /home/step/secrets/intermediate_ca_key
        address: ":9000"
        insecureAddress: ""
        dnsNames:
          - "step-ca.getbindu.com"
          - "step-ca.bindu-ca.svc.cluster.local"
        logger:
          format: json
        db:
          type: badgerv2
          dataSource: /home/step/db
        authority:
          provisioners: []  # Configured in Section 6
        tls:
          cipherSuites:
            - TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256
            - TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384
          minVersion: 1.2
          maxVersion: 1.3

# Liveness and readiness probes
livenessProbe:
  httpGet:
    path: /health
    port: 9000
    scheme: HTTPS
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health
    port: 9000
    scheme: HTTPS
  initialDelaySeconds: 5
  periodSeconds: 10

# Pod disruption budget for HA
podDisruptionBudget:
  enabled: true
  minAvailable: 1

# Anti-affinity: spread replicas across nodes
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchExpressions:
              - key: app.kubernetes.io/name
                operator: In
                values:
                  - step-certificates
          topologyKey: kubernetes.io/hostname
```

### 5.7 Deploy

```bash
# Install step-ca using Helm
helm install step-ca smallstep/step-certificates \
  --namespace bindu-ca \
  --values step-ca-values.yaml

# Verify pods are running
kubectl get pods -n bindu-ca

# Expected output:
# NAME                       READY   STATUS    RESTARTS   AGE
# step-ca-0                  1/1     Running   0          1m
# step-ca-1                  1/1     Running   0          1m

# Check step-ca health
kubectl port-forward -n bindu-ca svc/step-ca 9000:9000
curl -k https://localhost:9000/health
# Expected: {"status":"ok"}
```

---

## 6. OIDC Provisioner Configuration

The OIDC provisioner tells step-ca to trust tokens issued by Hydra. When an agent presents a valid Hydra OIDC token, step-ca issues an X.509 certificate.

### 6.1 Register step-ca as an OAuth2 Client in Hydra

step-ca needs to be registered as an OAuth2 client in Hydra so it can validate tokens:

```bash
# Register step-ca as a Hydra OAuth2 client
curl -X POST https://hydra-admin.getbindu.com/admin/clients \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "step-ca-provisioner",
    "client_name": "Smallstep CA OIDC Provisioner",
    "grant_types": ["client_credentials"],
    "response_types": ["token"],
    "scope": "openid",
    "token_endpoint_auth_method": "client_secret_post",
    "client_secret": "<GENERATE_A_STRONG_SECRET_HERE>"
  }'
```

**Generate the secret:**

```bash
openssl rand -base64 32
```

**Store the secret in Vault:**

```bash
vault kv put secret/bindu/step-ca/oidc-client \
  client_id=step-ca-provisioner \
  client_secret=<the-generated-secret>
```

### 6.2 Configure OIDC Provisioner in step-ca

Add the OIDC provisioner to step-ca's configuration. This can be done via the `step` CLI or by editing `ca.json`:

```bash
# Using step CLI (exec into the pod)
kubectl exec -it step-ca-0 -n bindu-ca -- \
  step ca provisioner add hydra \
    --type OIDC \
    --client-id step-ca-provisioner \
    --client-secret <secret-from-vault> \
    --configuration-endpoint https://hydra.getbindu.com/.well-known/openid-configuration \
    --domain getbindu.com \
    --listen-address :10000
```

**Or directly in `ca.json` (via ConfigMap):**

```json
{
  "authority": {
    "provisioners": [
      {
        "type": "OIDC",
        "name": "hydra",
        "clientID": "step-ca-provisioner",
        "clientSecret": "<secret-from-vault>",
        "configurationEndpoint": "https://hydra.getbindu.com/.well-known/openid-configuration",
        "admins": ["admin@getbindu.com"],
        "domains": ["getbindu.com"],
        "listenAddress": ":10000",
        "claims": {
          "maxTLSCertDuration": "24h",
          "defaultTLSCertDuration": "24h",
          "disableRenewal": false
        },
        "options": {
          "x509": {
            "templateFile": "/home/step/templates/agent-cert.tpl"
          }
        }
      },
      {
        "type": "ACME",
        "name": "acme",
        "claims": {
          "maxTLSCertDuration": "24h",
          "defaultTLSCertDuration": "24h"
        }
      }
    ]
  }
}
```

### 6.3 Certificate Template

Create a custom certificate template so that agent certificates contain the DID:

**File: `/home/step/templates/agent-cert.tpl`**

```json
{
  "subject": {
    "commonName": {{ toJson .Token.sub }}
  },
  "sans": {{ toJson .SANs }},
  "keyUsage": ["digitalSignature", "keyEncipherment"],
  "extKeyUsage": ["serverAuth", "clientAuth"]
}
```

**What this does:**
- `commonName` = the `sub` claim from the OIDC token = the agent's DID
- `SANs` = Subject Alternative Names (agent URL, DNS name)
- `clientAuth` + `serverAuth` = certificate valid for both sides of mTLS

**Store template as ConfigMap:**

```bash
kubectl create configmap step-ca-templates \
  --from-file=agent-cert.tpl=agent-cert.tpl \
  --namespace=bindu-ca
```

Mount in the Helm values:

```yaml
# Add to step-ca-values.yaml
extraVolumes:
  - name: templates
    configMap:
      name: step-ca-templates

extraVolumeMounts:
  - name: templates
    mountPath: /home/step/templates
    readOnly: true
```

### 6.4 Verify OIDC Provisioner

```bash
# Get a token from Hydra (simulating what an agent does)
TOKEN=$(curl -s -X POST https://hydra.getbindu.com/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=did:bindu:test:agent:123" \
  -d "client_secret=<agent-secret>" \
  -d "scope=openid" | jq -r .access_token)

echo "Token: $TOKEN"

# Request a certificate from step-ca using the OIDC token
step ca certificate \
  "did:bindu:test:agent:123" \
  agent.crt agent.key \
  --provisioner hydra \
  --token "$TOKEN" \
  --ca-url https://step-ca.getbindu.com \
  --root root_ca.crt

# Inspect the issued certificate
step certificate inspect agent.crt
```

**Expected output:**

```
Certificate:
    Data:
        Version: 3 (0x2)
        Serial Number: <random>
    Signature Algorithm: ECDSA-SHA256
        Issuer: CN=Bindu Intermediate CA
        Validity
            Not Before: 2026-03-24 ...
            Not After : 2026-03-25 ...   ← 24 hours
        Subject: CN=did:bindu:test:agent:123
        X509v3 extensions:
            X509v3 Subject Alternative Name:
                DNS:agent-name.getbindu.com
            X509v3 Key Usage: critical
                Digital Signature, Key Encipherment
            X509v3 Extended Key Usage:
                TLS Web Server Authentication
                TLS Web Client Authentication   ← allows both client and server
```

---

## 7. Root CA and Key Management

### 7.1 Trust Chain

```
Bindu Root CA (EC P-256, 10-year validity)
  │  Stored: Vault ONLY (secret/bindu/step-ca/root-ca)
  │  Purpose: Signs intermediate CA cert
  │  Rotation: Every 5 years (or on compromise)
  │
  └─► Bindu Intermediate CA (EC P-256, 5-year validity)
       │  Stored: step-ca pod (K8s secret step-ca-intermediate)
       │  Purpose: Signs agent certificates
       │  Rotation: Every 2 years (planned)
       │
       └─► Agent Certificate (EC P-256, 24-hour validity)
            │  Stored: Agent's .bindu/mtls/ directory
            │  Purpose: mTLS authentication + encryption
            │  Renewal: Automatic, every 16 hours
            │
            └─► Private Key (never leaves the agent)
```

### 7.2 Root CA Distribution

Every agent needs the root CA certificate to verify peer certificates during mTLS handshake. Distribution methods (in order of preference):

**Method 1: Fetch from step-ca at startup (recommended)**

```bash
# Agent fetches root CA cert from step-ca
step ca root root_ca.crt --ca-url https://step-ca.getbindu.com
```

The Bindu SDK does this automatically during `bindufy()`.

**Method 2: Bundle in pip package**

```
bindu/
  mtls/
    ca-bundle/
      root_ca.crt   # Bundled in the package
```

Simple but requires a package release to rotate.

**Method 3: Download from well-known URL**

```bash
curl -o root_ca.crt https://ca.getbindu.com/root.crt
```

Requires a static hosting endpoint for the root cert.

**Recommendation:** Method 1 (fetch from step-ca) with Method 2 as fallback.

### 7.3 Key Rotation Procedures

**Intermediate CA rotation (every 2 years):**

```bash
# 1. Generate new intermediate CA
step certificate create \
  "Bindu Intermediate CA v2" \
  intermediate_ca_v2.crt intermediate_ca_v2.key \
  --profile intermediate-ca \
  --ca root_ca.crt \
  --ca-key <from-vault> \
  --kty EC --curve P-256 \
  --not-after 43800h

# 2. Cross-sign: old intermediate signs new intermediate
#    (allows agents with old-intermediate-signed certs to verify new certs)

# 3. Update K8s secret
kubectl create secret tls step-ca-intermediate \
  --cert=intermediate_ca_v2.crt \
  --key=intermediate_ca_v2.key \
  --namespace=bindu-ca \
  --dry-run=client -o yaml | kubectl apply -f -

# 4. Rolling restart step-ca
kubectl rollout restart statefulset step-ca -n bindu-ca

# 5. Agents automatically get new certs on next renewal (within 24h)
```

**Root CA rotation (every 5 years or on compromise):**

This is more complex and requires federation. See Smallstep's root rotation guide.

---

## 8. Certificate Lifecycle

### 8.1 Issuance Flow

```
Agent (bindufy)                 Hydra                    step-ca
     │                            │                         │
     │  1. POST /oauth2/token     │                         │
     │  (client_credentials)      │                         │
     │───────────────────────────►│                         │
     │                            │                         │
     │  2. OIDC token             │                         │
     │◄───────────────────────────│                         │
     │                            │                         │
     │  3. Generate key pair locally (EC P-256)             │
     │  4. Create CSR (CN=DID, SAN=URL)                    │
     │                            │                         │
     │  5. POST /1.0/sign         │                         │
     │  (CSR + OIDC token)        │                         │
     │──────────────────────────────────────────────────────►
     │                            │                         │
     │                            │  6. Validate OIDC token │
     │                            │◄────────────────────────│
     │                            │  (check JWKS endpoint)  │
     │                            │────────────────────────►│
     │                            │                         │
     │                            │  7. Token valid ✅       │
     │                            │                         │
     │  8. Signed certificate     │                         │
     │  (cert.pem + ca-chain.pem) │                         │
     │◄──────────────────────────────────────────────────────
     │                            │                         │
     │  9. Store in .bindu/mtls/  │                         │
     │  10. Start uvicorn with TLS│                         │
     │  11. Start renewal thread  │                         │
```

### 8.2 Renewal Flow

```
Agent                                        step-ca
  │                                              │
  │  (every hour, check cert expiry)             │
  │                                              │
  │  cert expires in < 8 hours?                  │
  │  YES → initiate renewal                      │
  │                                              │
  │  POST /1.0/renew                             │
  │  (present current cert as mTLS client cert)  │
  │──────────────────────────────────────────────►│
  │                                              │
  │  step-ca verifies current cert is valid      │
  │  step-ca issues new cert (24h TTL)           │
  │                                              │
  │  New certificate                             │
  │◄──────────────────────────────────────────────│
  │                                              │
  │  Hot-swap cert in memory                     │
  │  Write new cert to .bindu/mtls/cert.pem      │
  │  (no server restart needed)                  │
```

**Renewal uses the current certificate as authentication** — no need to go back to Hydra for a new token. This is a step-ca feature called "passive renewal."

### 8.3 Revocation

step-ca uses **passive revocation** (short-lived certificates):

- Certificates are valid for 24 hours
- If an agent is compromised, revoke its Hydra OAuth2 client
- The agent cannot renew (renewal requires valid existing cert OR valid OIDC token)
- Within 24 hours, the compromised cert expires
- No CRL or OCSP infrastructure needed

**Emergency revocation (cannot wait 24h):**

```bash
# Revoke specific certificate by serial number
step ca revoke <serial-number> \
  --ca-url https://step-ca.getbindu.com \
  --root root_ca.crt

# Also revoke the Hydra OAuth2 client
curl -X DELETE https://hydra-admin.getbindu.com/admin/clients/<DID>
```

---

## 9. DNS and Networking

### 9.1 DNS Records

| Record | Type | Value | Purpose |
|--------|------|-------|---------|
| `step-ca.getbindu.com` | A / CNAME | Cluster ingress IP | step-ca API endpoint |
| `ca.getbindu.com` | A / CNAME | Same or CDN | Root CA cert download |

### 9.2 Kubernetes Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: step-ca
  namespace: bindu-ca
spec:
  type: ClusterIP
  ports:
    - name: https
      port: 9000
      targetPort: 9000
      protocol: TCP
  selector:
    app.kubernetes.io/name: step-certificates
```

### 9.3 Ingress (for external access)

Agents outside the cluster need to reach step-ca. Configure ingress with TLS passthrough (step-ca handles its own TLS):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: step-ca-ingress
  namespace: bindu-ca
  annotations:
    nginx.ingress.kubernetes.io/ssl-passthrough: "true"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
spec:
  rules:
    - host: step-ca.getbindu.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: step-ca
                port:
                  number: 9000
  tls:
    - hosts:
        - step-ca.getbindu.com
```

### 9.4 Network Policies

Lock down step-ca to only accept connections from:
- Agents (any namespace, port 9000)
- Hydra (for JWKS validation, outbound only)

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: step-ca-network-policy
  namespace: bindu-ca
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: step-certificates
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - ports:
        - port: 9000
          protocol: TCP
  egress:
    # Allow step-ca to reach Hydra for OIDC validation
    - to:
        - namespaceSelector:
            matchLabels:
              name: hydra
      ports:
        - port: 4444
          protocol: TCP
    # Allow DNS
    - to:
        - namespaceSelector: {}
      ports:
        - port: 53
          protocol: UDP
        - port: 53
          protocol: TCP
```

---

## 10. Monitoring and Alerting

### 10.1 Health Checks

```bash
# step-ca health endpoint
curl -k https://step-ca.getbindu.com/health
# Expected: {"status":"ok"}

# Check provisioner list
step ca provisioner list --ca-url https://step-ca.getbindu.com --root root_ca.crt
```

### 10.2 Prometheus Metrics

step-ca exposes metrics. Add scrape config:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'step-ca'
    scheme: https
    tls_config:
      ca_file: /path/to/root_ca.crt
    static_configs:
      - targets: ['step-ca.bindu-ca.svc.cluster.local:9000']
```

### 10.3 Alerts

| Alert | Condition | Severity | Action |
|-------|-----------|----------|--------|
| `StepCADown` | Health endpoint returns non-200 for > 2 min | Critical | Agents cannot get new certs |
| `StepCAHighLatency` | Cert issuance > 5s p99 | Warning | Check pod resources |
| `IntermediateCAExpiring` | Intermediate cert expires in < 90 days | Warning | Rotate intermediate |
| `RootCAExpiring` | Root cert expires in < 1 year | Critical | Plan root rotation |
| `CertIssuanceFailures` | > 10 failures in 5 minutes | Warning | Check OIDC provisioner / Hydra |
| `StepCADiskFull` | PV usage > 80% | Warning | Expand PV or clean DB |

### 10.4 Logging

step-ca logs in JSON format. Key log entries to monitor:

```json
{"level":"info","msg":"certificate signed","serial":"...","cn":"did:bindu:..."}
{"level":"info","msg":"certificate renewed","serial":"...","cn":"did:bindu:..."}
{"level":"warn","msg":"certificate request denied","reason":"invalid OIDC token"}
{"level":"error","msg":"OIDC validation failed","error":"JWKS fetch failed"}
```

**Set up log aggregation** (ELK, Loki, CloudWatch) to capture:
- Certificate issuance rate
- Renewal success/failure rate
- OIDC validation failures (may indicate Hydra issues)

---

## 11. Disaster Recovery

### 11.1 Backup Strategy

| Component | Backup Method | Frequency | Retention |
|-----------|--------------|-----------|-----------|
| Root CA key | Vault (already stored) | Once (immutable) | Forever |
| Root CA cert | Vault + git repo | Once (immutable) | Forever |
| Intermediate CA key | K8s secret backup | On rotation | Until next rotation |
| Intermediate CA cert | K8s secret backup | On rotation | Until next rotation |
| step-ca database | PV snapshot | Daily | 30 days |
| step-ca config | Git (Helm values) | On change | Forever |

### 11.2 Recovery Procedures

**step-ca pod crash/restart:**
- Automatic via K8s StatefulSet with persistent volume
- Certificates and database survive restarts
- Zero downtime with 2 replicas

**step-ca data loss (PV corrupted):**
1. Deploy fresh step-ca
2. Restore intermediate CA from K8s secret backup
3. Restore config from Helm values (git)
4. Database is lost (serial numbers, revocation list) — acceptable for passive revocation model
5. All existing agent certs remain valid until expiry

**Intermediate CA key compromised:**
1. Generate new intermediate CA (signed by root from Vault)
2. Deploy to step-ca
3. All agents auto-renew within 24 hours with new intermediate

**Root CA key compromised (worst case):**
1. Generate new root CA
2. Cross-sign new root with old root (if old root not fully compromised)
3. Generate new intermediate signed by new root
4. Deploy to step-ca
5. Distribute new root CA to all agents
6. All agents must restart to pick up new root

---

## 12. Security Hardening

### 12.1 step-ca Pod Security

```yaml
# Add to step-ca-values.yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop:
      - ALL
```

### 12.2 TLS Configuration

Enforce strong TLS settings:

```json
{
  "tls": {
    "cipherSuites": [
      "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256",
      "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384",
      "TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256"
    ],
    "minVersion": 1.2,
    "maxVersion": 1.3
  }
}
```

### 12.3 Certificate Constraints

```json
{
  "claims": {
    "minTLSCertDuration": "1h",
    "maxTLSCertDuration": "24h",
    "defaultTLSCertDuration": "24h",
    "disableRenewal": false
  }
}
```

- Minimum 1 hour (prevent abuse with very short certs)
- Maximum 24 hours (limit exposure window)
- Renewal enabled (agents auto-renew)

### 12.4 OIDC Provisioner Restrictions

```json
{
  "type": "OIDC",
  "name": "hydra",
  "domains": ["getbindu.com"],
  "admins": ["admin@getbindu.com"],
  "claims": {
    "maxTLSCertDuration": "24h"
  }
}
```

- `domains`: Only accept tokens from `@getbindu.com` identities
- `admins`: Only listed admins can request long-lived certs

---

## 13. Rollout Plan

### Week 1: Infrastructure

- [ ] Generate root CA and intermediate CA on secure offline machine
- [ ] Store root CA key in Vault
- [ ] Create K8s namespace `bindu-ca`
- [ ] Create K8s secrets (intermediate CA, root CA, password)
- [ ] Deploy step-ca via Helm
- [ ] Configure DNS: `step-ca.getbindu.com`
- [ ] Configure ingress with TLS passthrough
- [ ] Verify health endpoint: `curl -k https://step-ca.getbindu.com/health`

### Week 2: OIDC Integration

- [ ] Register step-ca as OAuth2 client in Hydra
- [ ] Store OIDC client credentials in Vault
- [ ] Configure OIDC provisioner in step-ca
- [ ] Create agent certificate template
- [ ] Verify: request test certificate using Hydra token
- [ ] Verify: inspect certificate has DID in CN

### Week 3: Monitoring

- [ ] Configure Prometheus scraping for step-ca
- [ ] Set up alerts (StepCADown, IntermediateCAExpiring, etc.)
- [ ] Set up log aggregation for step-ca JSON logs
- [ ] Test alert by simulating step-ca downtime
- [ ] Document backup procedures
- [ ] Test DR: kill step-ca pod, verify auto-recovery

### Week 4: Handoff to App Team

- [ ] Provide root CA certificate to application team
- [ ] Provide step-ca URL: `https://step-ca.getbindu.com`
- [ ] Provide OIDC provisioner name: `hydra`
- [ ] Document the API for certificate requests
- [ ] Walk through the issuance flow with app team
- [ ] Integration testing with Bindu app code

---

## 14. Verification Checklist

Run these commands after deployment to verify everything works:

```bash
# 1. step-ca is running
kubectl get pods -n bindu-ca
# Expected: 2/2 Running

# 2. Health check passes
curl -k https://step-ca.getbindu.com/health
# Expected: {"status":"ok"}

# 3. Root CA cert is fetchable
step ca root /tmp/test_root.crt --ca-url https://step-ca.getbindu.com --fingerprint <root-fingerprint>
step certificate inspect /tmp/test_root.crt
# Expected: CN=Bindu Root CA, valid for 10 years

# 4. OIDC provisioner is configured
step ca provisioner list --ca-url https://step-ca.getbindu.com --root /tmp/test_root.crt
# Expected: lists "hydra" provisioner of type OIDC

# 5. Can issue a certificate using Hydra token
TOKEN=$(curl -s -X POST https://hydra.getbindu.com/oauth2/token \
  -d "grant_type=client_credentials&client_id=<test-did>&client_secret=<test-secret>&scope=openid" \
  | jq -r .access_token)

step ca certificate "did:bindu:test:verify:001" /tmp/test.crt /tmp/test.key \
  --provisioner hydra \
  --token "$TOKEN" \
  --ca-url https://step-ca.getbindu.com \
  --root /tmp/test_root.crt

# 6. Certificate has correct fields
step certificate inspect /tmp/test.crt
# Expected:
#   Issuer: CN=Bindu Intermediate CA
#   Subject: CN=did:bindu:test:verify:001
#   Validity: 24 hours
#   Extended Key Usage: TLS Web Server Authentication, TLS Web Client Authentication

# 7. mTLS test between two certs
# Issue a second cert
step ca certificate "did:bindu:test:verify:002" /tmp/test2.crt /tmp/test2.key \
  --provisioner hydra \
  --token "$TOKEN2" \
  --ca-url https://step-ca.getbindu.com \
  --root /tmp/test_root.crt

# Start a test server with mTLS
openssl s_server -cert /tmp/test.crt -key /tmp/test.key -CAfile /tmp/test_root.crt \
  -Verify 1 -accept 8443

# Connect with client cert (new terminal)
openssl s_client -cert /tmp/test2.crt -key /tmp/test2.key -CAfile /tmp/test_root.crt \
  -connect localhost:8443
# Expected: Verify return code: 0 (ok)

# 8. Clean up test certs
rm /tmp/test*.crt /tmp/test*.key /tmp/test_root.crt
```

### All Green?

If all 8 checks pass, step-ca is ready. Hand off to the application team with:

1. **Root CA certificate** — agents need this to verify peers
2. **step-ca URL** — `https://step-ca.getbindu.com`
3. **OIDC provisioner name** — `hydra`
4. **Certificate template** — DID in CN, agent URL in SAN
5. **This document** — for ongoing operations

---

## Appendix A: Quick Reference

| Item | Value |
|------|-------|
| step-ca URL | `https://step-ca.getbindu.com` |
| step-ca port | 9000 |
| K8s namespace | `bindu-ca` |
| OIDC provisioner name | `hydra` |
| Root CA CN | `Bindu Root CA` |
| Root CA validity | 10 years |
| Root CA key location | Vault: `secret/bindu/step-ca/root-ca` |
| Intermediate CA CN | `Bindu Intermediate CA` |
| Intermediate CA validity | 5 years |
| Agent cert TTL | 24 hours |
| Agent cert renewal | 16 hours (8h before expiry) |
| Key type | EC P-256 |
| TLS min version | 1.2 |
| TLS max version | 1.3 |

## Appendix B: Useful Commands

```bash
# View step-ca logs
kubectl logs -n bindu-ca step-ca-0 -f

# Restart step-ca (rolling)
kubectl rollout restart statefulset step-ca -n bindu-ca

# Check intermediate CA expiry
kubectl exec -n bindu-ca step-ca-0 -- step certificate inspect /home/step/certs/intermediate_ca.crt

# List all issued certificates (from step-ca DB)
kubectl exec -n bindu-ca step-ca-0 -- step ca admin list

# Revoke a certificate
step ca revoke <serial-number> --ca-url https://step-ca.getbindu.com --root root_ca.crt

# Force-renew an agent cert (from agent machine)
step ca renew cert.pem key.pem --force --ca-url https://step-ca.getbindu.com --root root_ca.crt
```
