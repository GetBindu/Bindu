## Summary

Describe the problem and fix in 2–5 bullets:

- **Problem**:
- **Why it matters**:
- **What changed**:
- **What did NOT change** (scope boundary):

## Change Type (select all that apply)

- [ ] Bug fix
- [ ] Feature
- [ ] Refactor
- [ ] Documentation
- [ ] Security hardening
- [ ] Tests
- [ ] Chore/infra

## Scope (select all touched areas)

- [ ] Server / API endpoints
- [ ] Extensions (DID, x402, etc.)
- [ ] Storage backends
- [ ] Scheduler backends
- [ ] Observability / monitoring
- [ ] Authentication / authorization
- [ ] CLI / utilities
- [ ] Tests
- [ ] Documentation
- [ ] CI/CD / infra

## Linked Issue/PR

- Closes #
- Related #

## User-Visible / Behavior Changes

List user-visible changes (including defaults/config).
If none, write `None`.

## Security Impact (required)

- New permissions/capabilities? (`Yes/No`)
- Secrets/credentials handling changed? (`Yes/No`)
- New/changed network calls? (`Yes/No`)
- Database schema/migration changes? (`Yes/No`)
- Authentication/authorization changes? (`Yes/No`)
- **If any `Yes`, explain risk + mitigation**:

## Verification

### Environment

- OS:
- Python version:
- Storage backend:
- Scheduler backend:

### Steps to Test

1.
2.
3.

### Expected Behavior

-

### Actual Behavior

-

## Evidence (attach at least one)

- [ ] Failing test before + passing after
- [ ] Test output / logs
- [ ] Screenshot / recording
- [ ] Performance metrics (if relevant)

## Human Verification (required)

What you personally verified (not just CI):

- **Verified scenarios**:
- **Edge cases checked**:
- **What you did NOT verify**:

## Compatibility / Migration

- Backward compatible? (`Yes/No`)
- Config/env changes? (`Yes/No`)
- Database migration needed? (`Yes/No`)
- **If yes, exact upgrade steps**:

## Failure Recovery (if this breaks)

- How to disable/revert this change quickly:
- Files/config to restore:
- Known bad symptoms reviewers should watch for:

## Risks and Mitigations

List only real risks for this PR. If none, write `None`.

- **Risk**:
  - **Mitigation**:

## Checklist

- [ ] Tests pass (`uv run pytest`)
- [ ] Pre-commit hooks pass (`uv run pre-commit run --all-files`)
- [ ] Documentation updated (if needed)
- [ ] Security impact assessed
- [ ] Human verification completed
- [ ] Backward compatibility considered
