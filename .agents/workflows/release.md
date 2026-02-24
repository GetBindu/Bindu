---
description: Create releases with week-based versioning (YYYY.Week.Day)
---

# Bindu Release Workflow

Quick workflow to create releases using week-based versioning: `YYYY.W.D`

## Quick Start

```bash
# Generate version (Year.Week.DayOfWeek)
VERSION=$(date +%Y.%-V.%-u)  # e.g., 2026.8.3

# Create release notes
vim release-notes/$VERSION.txt

# Create and push tag
git tag -a $VERSION -F release-notes/$VERSION.txt
git push origin $VERSION

# Create GitHub release
gh release create $VERSION \
  --notes-file release-notes/$VERSION.txt \
  --title "$VERSION: Release Title"
```

---

## Versioning Format

**Week-based**: `YYYY.W.D`
- YYYY = Year (2026)
- W = ISO week number (1-53)
- D = Day of week (1=Sunday, 7=Saturday)

Examples: `2026.8.3` (Wed, Week 8), `2026.52.5` (Fri, Week 52)

---

## Steps

### 1. Pre-Release Checks

```bash
# Run tests and hooks
uv run pytest
uv run pre-commit run --all-files

# Verify clean state
git status
git pull origin main
```

### 2. Create Release Notes

```bash
VERSION=$(date +%Y.%-V.%-u)
vim release-notes/$VERSION.txt
```

Minimal template:
```
Release: [Title]
Version: YYYY.W.D
Date: Month Day, Year

OVERVIEW
--------
Brief description.

CHANGES
-------
- Change 1
- Change 2

TESTING
-------
✅ All tests passing
```

### 3. Create and Push Release

```bash
VERSION=$(date +%Y.%-V.%-u)

# Create tag
git tag -a $VERSION -F release-notes/$VERSION.txt

# Push tag
git push origin $VERSION

# Create GitHub release
gh release create $VERSION \
  --notes-file release-notes/$VERSION.txt \
  --title "$VERSION: Release Title"
```

---

## Quick Commands

```bash
# One-liner release (after creating release notes)
VERSION=$(date +%Y.%-V.%-u) && \
git tag -a $VERSION -F release-notes/$VERSION.txt && \
git push origin $VERSION && \
gh release create $VERSION --notes-file release-notes/$VERSION.txt
```
