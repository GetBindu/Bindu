# Agent Trust Configuration

Agent Trust Configuration defines security policies and trust requirements for agent deployments. This ensures proper verification of agent identities and enforces operational constraints to prevent unauthorized or risky agent compositions.

## Overview

Trust configuration manages:
- **Verification Levels**: Required trust/authorization levels for agents to operate
- **Origin Control**: Which domains can invoke your agent
- **Hierarchy Constraints**: Maximum nesting depth for agent-to-agent calls
- **Verification Requirements**: Whether explicit trust verification is required
- **Certificate Requirements**: Whether security certificates are mandatory

## Configuration Structure

Trust configuration is specified in the agent's configuration file under the `agent_trust` field:

```json
{
  "author": "agent@example.com",
  "deployment": {},
  "agent_trust": {
    "identity_provider": "hydra",
    "required_verification_level": "manager",
    "allowed_origins": [
      "https://api.example.com",
      "https://*.getbindu.com"
    ],
    "max_agent_hierarchy_depth": 5,
    "trust_verification_required": true,
    "certificate_required": true,
    "metadata": {
      "region": "us-east-1",
      "compliance_level": "high"
    }
  }
}
```

## Configuration Fields

### identity_provider (Optional)
**Type:** `string`  
**Default:** `"hydra"`  
**Supported Values:** `"hydra"`

Specifies the identity provider used for agent trust verification. Currently, only Hydra is supported.

**Example:**
```json
"identity_provider": "hydra"
```

### required_verification_level (Required)
**Type:** `string`  
**Required:** Yes

The minimum authorization level required for agents to perform operations.

**Supported Levels:**
- `"viewer"` - View-only access, minimal permissions
- `"guest"` - Limited access, read-only operations
- `"analyst"` - Standard read operations
- `"editor"` - Edit operations, moderate risk
- `"operator"` - System operations, moderate risk
- `"manager"` - Management operations, elevated permissions
- `"auditor"` - Sensitive operations, audit access
- `"admin"` - Admin operations, minimal risk
- `"support"` - Support operations, troubleshooting access
- `"super_admin"` - Highest level access, all operations permitted

**Example - Production Agent:**
```json
"required_verification_level": "manager"
```

**Example - Public Agent:**
```json
"required_verification_level": "guest"
```

### allowed_origins (Optional)
**Type:** `array[string]`  
**Default:** Empty (all origins allowed)

List of allowed domains/origins that can invoke this agent. Supports wildcard patterns.

**Format:**
- Full domain: `"https://example.com"`
- Wildcard subdomains: `"https://*.example.com"`
- Wildcards must use `https://` or `http://` prefix

**Example - Single Origin:**
```json
"allowed_origins": ["https://api.example.com"]
```

**Example - Multiple Origins:**
```json
"allowed_origins": [
  "https://api.example.com",
  "https://admin.example.com",
  "https://*.example.com"
]
```

**Example - Internal Network:**
```json
"allowed_origins": [
  "https://*.internal.example.com",
  "https://trusted-partner.com"
]
```

### max_agent_hierarchy_depth (Required)
**Type:** `integer`  
**Required:** Yes  
**Constraints:** Must be >= 1

Maximum nesting depth for agent-to-agent calls. Prevents circular dependencies and infinite loops when agents call other agents.

**Value Guide:**
- `1` - No agent-to-agent calls allowed (only direct calls)
- `3` - Shallow hierarchy (A → B → C)
- `5` - Standard (most deployments)
- `10` - Deep hierarchies (complex workflows)

**Example - Shallow Hierarchy:**
```json
"max_agent_hierarchy_depth": 1
```

**Example - Standard Hierarchy:**
```json
"max_agent_hierarchy_depth": 5
```

**Example - Deep Hierarchy:**
```json
"max_agent_hierarchy_depth": 10
```

### trust_verification_required (Optional)
**Type:** `boolean`  
**Default:** `false`

Whether explicit trust verification must be completed before the agent can execute operations. When `true`, agents must verify trust relationships before processing tasks.

**Example - Requiring Verification:**
```json
"trust_verification_required": true
```

**Example - No Verification Needed:**
```json
"trust_verification_required": false
```

### certificate_required (Optional)
**Type:** `boolean`  
**Default:** `false`

Whether agent security certificates are required for operation. When `true`, agents must provide valid certificates for authentication.

**Example - Certificate Required:**
```json
"certificate_required": true
```

### metadata (Optional)
**Type:** `object`  
**Default:** `{}`

Custom metadata for deployment-specific trust requirements. Not validated by the system but available for custom implementations.

**Example - Compliance Metadata:**
```json
"metadata": {
  "region": "us-east-1",
  "compliance_level": "high",
  "data_residency": "us-only",
  "audit_required": true,
  "soc2_certified": true
}
```

**Example - Business Metadata:**
```json
"metadata": {
  "owner": "security-team",
  "approval_required": true,
  "approval_ticket": "SECURITY-123",
  "review_date": "2025-01-15",
  "risk_level": "medium"
}
```

## Validation Rules

The ConfigValidator enforces the following rules:

### Required Fields
- `required_verification_level` - Must be one of the valid levels above
- `max_agent_hierarchy_depth` - Must be a positive integer (>= 1)

### Type Validation
- `identity_provider` - String, must be "hydra" if provided
- `allowed_origins` - List of strings, each must start with http:// or https://, or contain wildcard
- `trust_verification_required` - Boolean
- `certificate_required` - Boolean
- `metadata` - Dictionary/object

### Domain Validation
- Origins must be valid URL format: `http://...` or `https://...`
- Wildcards allowed in origin domains only: `https://*.example.com`
- Each origin must be a non-empty string

## Example Configurations

### Development Agent (Minimal Trust)
For development and testing with minimal restrictions:

```json
{
  "author": "dev@example.com",
  "deployment": {},
  "agent_trust": {
    "required_verification_level": "viewer",
    "max_agent_hierarchy_depth": 1,
    "trust_verification_required": false,
    "certificate_required": false
  }
}
```

### Production Agent (Standard Trust)
For regular production deployments:

```json
{
  "author": "prod@example.com",
  "deployment": {},
  "agent_trust": {
    "identity_provider": "hydra",
    "required_verification_level": "manager",
    "allowed_origins": [
      "https://api.example.com",
      "https://*.example.com"
    ],
    "max_agent_hierarchy_depth": 5,
    "trust_verification_required": true,
    "certificate_required": false
  }
}
```

### High-Security Agent
For sensitive operations with strict requirements:

```json
{
  "author": "security@example.com",
  "deployment": {},
  "agent_trust": {
    "identity_provider": "hydra",
    "required_verification_level": "super_admin",
    "allowed_origins": [
      "https://secure.example.com",
      "https://admin.internal.example.com"
    ],
    "max_agent_hierarchy_depth": 2,
    "trust_verification_required": true,
    "certificate_required": true,
    "metadata": {
      "compliance_level": "high",
      "audit_required": true,
      "soc2_certified": true,
      "data_classification": "confidential"
    }
  }
}
```

### Multi-Tenant Agent
For agents serving multiple customers:

```json
{
  "author": "platform@example.com",
  "deployment": {},
  "agent_trust": {
    "required_verification_level": "analyst",
    "allowed_origins": [
      "https://tenant-1.example.com",
      "https://tenant-2.example.com",
      "https://tenant-3.example.com",
      "https://*.tenant.example.com"
    ],
    "max_agent_hierarchy_depth": 3,
    "trust_verification_required": true,
    "certificate_required": true,
    "metadata": {
      "multi_tenant": true,
      "isolation_level": "strict",
      "rate_limiting": "per_tenant"
    }
  }
}
```

## Implementation

Trust configuration is processed during agent initialization through the `ConfigValidator` class:

```python
from bindu.penguin.config_validator import ConfigValidator

# Load raw configuration
config = load_config_from_file("agent_config.json")

# Validate and process - trust config is validated here
validated_config = ConfigValidator.validate_and_process(config)

# Trust configuration is now available
trust_config = validated_config["agent_trust"]
print(f"Required level: {trust_config['required_verification_level']}")
print(f"Max hierarchy depth: {trust_config['max_agent_hierarchy_depth']}")
```

## Validation Errors

### Missing Required Field Example
```
ValueError: Invalid agent_trust configuration: Required key 'required_verification_level' missing.
```

**Solution:** Add the required field to your `agent_trust` configuration.

### Invalid Verification Level Example
```
ValueError: Invalid required_verification_level: 'invalid_level'.
Must be one of: admin, analyst, auditor, editor, guest, manager, operator, super_admin, support, viewer
```

**Solution:** Choose a valid level from the supported list.

### Invalid Hierarchy Depth Example
```
ValueError: Invalid max_agent_hierarchy_depth: '0'. Must be a positive integer (>= 1)
```

**Solution:** Set a positive integer value (minimum 1).

### Invalid Origin Format Example
```
ValueError: Invalid origin format: 'example.com'. Expected http:// or https:// URL or wildcard pattern
```

**Solution:** Ensure all origins start with `http://` or `https://`.

## Best Practices

1. **Principle of Least Privilege**: Use the minimum verification level needed
   - Use `viewer` or `guest` for read-only operations
   - Use `manager` or `editor` for standard operations
   - Use `admin` or `super_admin` only for critical operations

2. **Origin Control**: Always restrict origins in production
   - Use specific domains instead of wildcard `*`
   - Use subdomain wildcards: `https://*.example.com`
   - Document why each origin needs access

3. **Hierarchy Depth**: Keep nesting shallow
   - Default to `5` for most deployments
   - Use `1-2` for simple agents
   - Use `>8` only for complex workflows

4. **Verification**: Enable for production
   - Set `trust_verification_required: true` in production
   - Set `trust_verification_required: false` for development only
   - Review verification requirements regularly

5. **Certificates**: Use in sensitive deployments
   - Enable `certificate_required: true` for financial operations
   - Enable for healthcare or regulated data
   - Disable for development/testing

6. **Documentation**: Keep metadata updated
   - Document compliance requirements
   - Track approval decisions
   - Record review dates
   - Maintain audit trail

## Related Documentation

- [Authentication](./AUTHENTICATION.md) - User/agent authentication with Hydra
- [DID](./DID.md) - Decentralized Identity for agents
- [Security Best Practices](./SECURITY.md) - Broader security guidelines
- [Configuration Guide](../README.md#configuration) - Overall configuration reference
