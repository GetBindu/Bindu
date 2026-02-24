---
name: test-pr
description: Test pull requests with comprehensive validation and generate structured test results
---

# Test PR Skill

## Overview

Test a pull request to ensure code quality, functionality, and compatibility before merging.

## Inputs

- PR number or URL
- Optional: specific test patterns to run

## Safety

- Never modify code in this skill
- Only read and test
- Generate artifacts in `.local/` directory
- Do not push changes

## Execution Contract

1. Fetch PR metadata
2. Checkout PR branch in isolated worktree
3. Install dependencies
4. Run test suite
5. Run pre-commit hooks
6. Generate structured test results
7. Output recommendation

## Steps

### 1. Initialize PR Testing

```bash
# Get PR metadata
PR_NUMBER=$1
gh pr view $PR_NUMBER --json number,title,author,headRefName,baseRefName > .local/pr-meta.json

# Create isolated worktree
git worktree add .worktrees/pr-$PR_NUMBER origin/main
cd .worktrees/pr-$PR_NUMBER

# Fetch PR branch
git fetch origin pull/$PR_NUMBER/head:pr-$PR_NUMBER
git checkout pr-$PR_NUMBER
```

### 2. Install Dependencies

```bash
# Install with frozen lockfile
uv sync --frozen

# Verify installation
uv run python -c "import bindu; print(bindu.__version__)"
```

### 3. Run Test Suite

```bash
# Run all tests with coverage
uv run pytest --cov=bindu --cov-report=json --json-report --json-report-file=.local/test-results.json

# Extract coverage percentage
COVERAGE=$(jq -r '.totals.percent_covered' coverage.json)
echo "Coverage: $COVERAGE%"
```

### 4. Run Pre-Commit Hooks

```bash
# Run all hooks
uv run pre-commit run --all-files > .local/precommit-results.txt 2>&1

# Check exit code
if [ $? -eq 0 ]; then
    echo "✅ All pre-commit hooks passed"
else
    echo "❌ Some pre-commit hooks failed"
fi
```

### 5. Check for Common Issues

```bash
# Check for print statements (should use logger)
grep -r "print(" bindu/ --include="*.py" | grep -v "# noqa" || echo "✅ No print statements"

# Check for TODO comments
grep -r "TODO\|FIXME\|XXX" bindu/ --include="*.py" || echo "✅ No TODO comments"

# Check for hardcoded credentials
uv run detect-secrets scan bindu/ || echo "⚠️ Potential secrets detected"

# Check for type hints
grep -r "def.*->.*:" bindu/ --include="*.py" | wc -l
```

### 6. Generate Structured Results

Create `.local/test-report.json`:

```json
{
  "pr_number": 123,
  "recommendation": "READY FOR MERGE",
  "findings": [
    {
      "id": "F1",
      "severity": "INFO",
      "title": "All tests passing",
      "area": "tests",
      "details": "100% test pass rate with 68% coverage"
    }
  ],
  "tests": {
    "total": 150,
    "passed": 150,
    "failed": 0,
    "skipped": 0,
    "coverage": 68.5,
    "result": "pass"
  },
  "precommit": {
    "hooks_passed": 8,
    "hooks_failed": 0,
    "result": "pass"
  },
  "quality": {
    "print_statements": 0,
    "todo_comments": 2,
    "type_coverage": 85
  }
}
```

### 7. Output Recommendation

Based on findings:

- **READY FOR MERGE**: All tests pass, hooks pass, no blockers
- **NEEDS WORK**: Tests fail or critical issues found
- **NEEDS DISCUSSION**: Design concerns or unclear requirements

## Output Format

```markdown
# PR #123 Test Results

## Summary
✅ All tests passing (150/150)
✅ Coverage: 68.5% (above 66% threshold)
✅ All pre-commit hooks passing
⚠️ 2 TODO comments found

## Recommendation
READY FOR MERGE

## Test Details
- Unit tests: 120 passed
- Integration tests: 30 passed
- Coverage: 68.5%

## Quality Checks
- ✅ No print statements
- ⚠️ 2 TODO comments
- ✅ Type hints: 85% coverage

## Next Steps
1. Review TODO comments
2. Proceed with merge
```

## Artifacts Generated

- `.local/pr-meta.json` - PR metadata
- `.local/test-results.json` - Test execution results
- `.local/test-report.json` - Structured findings
- `.local/precommit-results.txt` - Pre-commit output

## Guardrails

- Do not modify code
- Do not push changes
- Do not merge PR
- Only test and report
- Clean up worktree after testing

## Example Usage

```bash
# Test PR #123
/skill test-pr 123

# Test with specific pattern
/skill test-pr 123 --pattern "test_applications"
```
