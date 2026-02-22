# Secret Finder Skill

## Overview
The Secret Finder is a Bindu-compatible security agent designed to scan text and code snippets for accidentally leaked secrets, passwords and API keys.

## Capabilities
- **search_secrets**: Scans incoming text against a list of known sensitive keywords (`password`, `api_key`, `token`, etc).
- **security_audit**: Returns a structured JSON response indicating whether the text is safe, alongside any detected vulnerabilities.

## Usage Example
When deployed, other agents can request this skill to verify their outputs before sending data over the network or saving it to logs.

```json
{
  "is_safe": false,
  "found_words": ["api_key"],
  "warning": "🚨 SECRET DETECTED!"
}
```

## Setup
No external API keys are required for the standalone scanning logic.
