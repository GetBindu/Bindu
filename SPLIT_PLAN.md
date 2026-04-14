# Voice Agent Split Plan

This document captures the current PR splitting strategy for the voice-agent work.

## Goal

Split the work into a ladder of dependent PRs so each review only shows the incremental changes on top of the previous layer.

## Current Branch Order

1. Core code branch
2. Example-agent branch
3. Documentation branch

Package and dependency updates are kept separate unless they are required for the stacked feature chain.

## Rules

- Use the existing backup branch already created and pushed; do not create another backup branch.
- Build each new branch from the previous ladder branch, not from `main`.
- Keep each PR focused on one layer of change.
- Use `git cherry-pick -n <sha>` and path-level cleanup when a commit mixes multiple concerns.

## PR Stack

### 1. Core Code PR

- Base branch: `main`
- Head branch: first ladder branch
- Scope: core runtime and frontend code needed for the voice-agent feature
- Review goal: establish the foundational implementation

### 2. Example-Agent PR

- Base branch: the core code branch
- Head branch: second ladder branch
- Scope: example-agent files only
- Review goal: show only the example-specific delta on top of the core implementation

### 3. Documentation PR

- Base branch: the example-agent branch
- Head branch: third ladder branch
- Scope: docs only
- Review goal: show only the documentation delta on top of the example-agent layer

## Verification

For each branch:

1. Run `uv run pre-commit run --all-files`
2. Run any targeted tests for touched code
3. Confirm the GitHub compare view only shows the incremental diff from the chosen base branch

## Notes

- The backup branch exists as a safety snapshot.
- The ladder branches are standalone review layers, not cumulative PRs against `main`.
- If package/dependency changes become required, handle them in a separate branch/PR stream unless they must be part of the ladder chain.
