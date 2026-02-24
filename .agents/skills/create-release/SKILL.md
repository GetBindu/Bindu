---
name: create-release
description: Create releases with proper versioning, release notes, and Git tags
---

# Create Release Skill

## Overview

Create a new Bindu release with CalVer versioning, comprehensive release notes, and Git tags.

## Inputs

- Optional: Version number (defaults to current date in YYYY.Week.Day format)
- Optional: Release title

## Safety

- Never create release without passing tests
- Verify no uncommitted changes
- Ensure on main branch
- Generate deterministic release notes
- Create annotated Git tags

## Execution Contract

1. Validate pre-release conditions
2. Determine version number
3. Generate release notes
4. Create Git tag
5. Push tag to remote
6. Create GitHub release
7. Generate release record

## Steps

### 1. Pre-Release Validation

```bash
# Ensure all tests pass
echo "==> Running tests..."
uv run pytest || { echo "❌ Tests failed"; exit 1; }

# Run pre-commit hooks
echo "==> Running pre-commit hooks..."
uv run pre-commit run --all-files || { echo "❌ Pre-commit hooks failed"; exit 1; }

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    echo "❌ Error: Uncommitted changes detected"
    git status --short
    exit 1
fi

# Verify on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "❌ Error: Not on main branch (currently on $CURRENT_BRANCH)"
    exit 1
fi

# Pull latest changes
git pull origin main
```

### 2. Determine Version Number

```bash
# Use provided version or generate from date
if [ -z "$1" ]; then
    VERSION=$(date +%Y.%W.%-d)
else
    VERSION=$1
fi

echo "Version: $VERSION"

# Check if tag already exists
if git rev-parse "$VERSION" >/dev/null 2>&1; then
    echo "❌ Error: Tag $VERSION already exists"
    exit 1
fi

# Get last release tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
echo "Last release: $LAST_TAG"
```

### 3. Collect Changes Since Last Release

```bash
# Get commit log
if [ -n "$LAST_TAG" ]; then
    COMMITS=$(git log $LAST_TAG..HEAD --pretty=format:"  - %h: %s" --reverse)
    FILE_CHANGES=$(git diff $LAST_TAG..HEAD --stat)
    LINES_ADDED=$(git diff $LAST_TAG..HEAD --numstat | awk '{added+=$1} END {print added}')
    LINES_REMOVED=$(git diff $LAST_TAG..HEAD --numstat | awk '{removed+=$2} END {print removed}')
    FILES_MODIFIED=$(git diff $LAST_TAG..HEAD --name-only | wc -l)
else
    COMMITS=$(git log --pretty=format:"  - %h: %s" --reverse)
    FILE_CHANGES=$(git diff --stat)
    LINES_ADDED="N/A"
    LINES_REMOVED="N/A"
    FILES_MODIFIED=$(git ls-files | wc -l)
fi

# Categorize commits
BREAKING_CHANGES=$(echo "$COMMITS" | grep -i "breaking\|BREAKING" || echo "")
FEATURES=$(echo "$COMMITS" | grep -i "feat:\|feature:" || echo "")
FIXES=$(echo "$COMMITS" | grep -i "fix:\|bugfix:" || echo "")
REFACTORS=$(echo "$COMMITS" | grep -i "refactor:" || echo "")
CHORES=$(echo "$COMMITS" | grep -i "chore:" || echo "")
```

### 4. Generate Release Notes

Create `release-notes/$VERSION.txt`:

```bash
cat > release-notes/$VERSION.txt <<EOF
Release: ${RELEASE_TITLE:-"Release $VERSION"}
====================================================

Version: $VERSION
Date: $(date +"%B %d, %Y")
Author: $(git config user.name)

OVERVIEW
--------
${RELEASE_OVERVIEW:-"This release includes bug fixes, improvements, and new features."}

BREAKING CHANGES
----------------
$(if [ -n "$BREAKING_CHANGES" ]; then echo "$BREAKING_CHANGES"; else echo "None"; fi)

IMPROVEMENTS
------------
🎯 Features
$(if [ -n "$FEATURES" ]; then echo "$FEATURES"; else echo "  - No new features"; fi)

🐛 Bug Fixes
$(if [ -n "$FIXES" ]; then echo "$FIXES"; else echo "  - No bug fixes"; fi)

🔧 Refactoring
$(if [ -n "$REFACTORS" ]; then echo "$REFACTORS"; else echo "  - No refactoring"; fi)

📦 Chores
$(if [ -n "$CHORES" ]; then echo "$CHORES"; else echo "  - No chores"; fi)

TECHNICAL DETAILS
-----------------
Files Modified: $FILES_MODIFIED files

Code Metrics:
  Total Lines Added: +$LINES_ADDED
  Total Lines Removed: -$LINES_REMOVED
  Files Modified: $FILES_MODIFIED
  Production Functionality: 100% preserved

TESTING
-------
✅ All unit tests passing
✅ All integration tests passing
✅ Pre-commit hooks passing
✅ No regression in existing functionality

COMMIT DETAILS
--------------
Key Commits:
$COMMITS

USAGE WITH GIT
--------------
# Create an annotated tag
git tag -a $VERSION -F release-notes/$VERSION.txt

# Create a GitHub release
gh release create $VERSION \\
  --notes-file release-notes/$VERSION.txt \\
  --title "$VERSION: ${RELEASE_TITLE:-Release}"

# View this release
git show $VERSION

# Push tag to remote
git push origin $VERSION
EOF

echo "✅ Release notes created: release-notes/$VERSION.txt"
```

### 5. Review Release Notes

```bash
# Display release notes for review
echo "==> Release Notes Preview:"
cat release-notes/$VERSION.txt

# Prompt for confirmation
read -p "Create release with these notes? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Release creation cancelled"
    exit 1
fi
```

### 6. Create Git Tag

```bash
# Create annotated tag
git tag -a $VERSION -F release-notes/$VERSION.txt

# Verify tag
git tag -l $VERSION
echo "✅ Git tag created: $VERSION"
```

### 7. Push Tag to Remote

```bash
# Push tag
git push origin $VERSION

# Verify tag on remote
git ls-remote --tags origin | grep $VERSION
echo "✅ Tag pushed to remote: $VERSION"
```

### 8. Create GitHub Release

```bash
# Create GitHub release
TITLE="${RELEASE_TITLE:-Release $VERSION}"

gh release create $VERSION \
  --notes-file release-notes/$VERSION.txt \
  --title "$VERSION: $TITLE"

# Verify release
gh release view $VERSION
echo "✅ GitHub release created: $VERSION"
```

### 9. Generate Release Record

Create `.local/release.json`:

```json
{
  "version": "$VERSION",
  "date": "$(date -Iseconds)",
  "title": "$TITLE",
  "commit": "$(git rev-parse HEAD)",
  "previous_version": "$LAST_TAG",
  "changes": {
    "commits": $(echo "$COMMITS" | wc -l),
    "files_modified": $FILES_MODIFIED,
    "lines_added": $LINES_ADDED,
    "lines_removed": $LINES_REMOVED
  },
  "categories": {
    "breaking_changes": $(echo "$BREAKING_CHANGES" | wc -l),
    "features": $(echo "$FEATURES" | wc -l),
    "fixes": $(echo "$FIXES" | wc -l),
    "refactors": $(echo "$REFACTORS" | wc -l)
  },
  "status": "published",
  "github_url": "https://github.com/GetBindu/Bindu/releases/tag/$VERSION"
}
```

## Output Format

```markdown
# Release Created: $VERSION

## Summary
- Version: $VERSION
- Date: $(date +"%B %d, %Y")
- Commits since last release: X
- Files modified: Y

## Changes
- Breaking changes: N
- Features: N
- Bug fixes: N
- Refactors: N

## Status
✅ Release notes created
✅ Git tag created and pushed
✅ GitHub release published

## Links
- Release: https://github.com/GetBindu/Bindu/releases/tag/$VERSION
- Tag: https://github.com/GetBindu/Bindu/tree/$VERSION

## Next Steps
1. Announce release
2. Update documentation
3. Monitor for issues
```

## Artifacts Generated

- `release-notes/$VERSION.txt` - Release notes
- `.local/release.json` - Release metadata
- Git tag: `$VERSION`
- GitHub release

## Guardrails

- Never create release without passing tests
- Always verify on main branch
- Always check for uncommitted changes
- Generate comprehensive release notes
- Create annotated tags (not lightweight)
- Verify tag pushed successfully

## Example Usage

```bash
# Create release with auto-generated version
/skill create-release

# Create release with specific version
/skill create-release 2026.8.1

# Create release with title
/skill create-release 2026.8.1 "Major Feature Release"
```
