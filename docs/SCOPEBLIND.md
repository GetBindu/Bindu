# ScopeBlind Authorization Receipts

ScopeBlind adds verifiable authorization receipts to Bindu agents.

It complements DID signing instead of replacing it:

- DID answers: "Which agent produced this artifact?"
- ScopeBlind answers: "Was this action authorized under the configured policy?"

## What It Does

- Evaluates Cedar policies before task execution
- Blocks denied actions in `enforce` mode
- Logs denied actions but still executes in `shadow` mode
- Signs a deterministic receipt with a dedicated Ed25519 key
- Attaches receipts to completed task metadata and artifact metadata
- Supports verification without depending on the agent DID key

## Configuration

Use top-level `scopeblind` config in `bindufy()`:

```python
from bindu.penguin.bindufy import bindufy

config = {
    "author": "you@example.com",
    "name": "policy-agent",
    "deployment": {"url": "http://localhost:3773"},
    "scopeblind": {
        "mode": "enforce",
        "cedar_policies": "./policies",
    },
}

bindufy(config, handler)
```

You can also add a `ScopeBlindExtension` directly to `capabilities.extensions` if you are assembling capabilities manually.

## Cedar Policies

ScopeBlind accepts either:

- a directory containing `*.cedar` files
- a single Cedar policy file path
- an inline Cedar policy string

Example policy:

```cedar
permit(principal, action == Action::"message/send", resource);
```

Example deny policy:

```cedar
forbid(principal, action == Action::"message/send", resource);
```

## Receipt Metadata

Completed tasks and artifacts include metadata under:

- `scopeblind.receipts`
- `scopeblind.decision`
- `scopeblind.mode`
- `scopeblind.policy_hash`

The receipt payload includes:

- principal, action, resource, and context
- the policy hash used for evaluation
- the final decision
- artifact digests covered by the receipt
- a detached Ed25519 signature over the payload hash

## Verification

Verify receipts with the helper functions:

```python
from bindu.extensions.scopeblind import verify_receipt, verify_artifact_receipt

receipt_result = verify_receipt(receipt_dict)
artifact_result = verify_artifact_receipt(artifact_dict, receipt_dict)
```

Verification checks:

- payload hash integrity
- Ed25519 signature validity
- artifact digest integrity

## Key Separation

ScopeBlind uses its own signing key material under `.scopeblind/`.

This is intentionally separate from the DID extension so identity and authorization remain distinct.
