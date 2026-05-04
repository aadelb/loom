## Description

<!-- Brief, clear summary of the changes. Focus on the "why" not just the "what" -->

## Issue Link

Closes #

<!-- Reference the issue(s) this PR addresses using GitHub issue linking -->

## Changes Made

<!-- Detailed list of changes, organized by area -->

### Core Changes
- [ ] Change 1
- [ ] Change 2
- [ ] Change 3

### Documentation
- [ ] README.md updated
- [ ] Docstrings added/updated
- [ ] CHANGELOG.md entry added
- [ ] Inline comments for complex logic

### Tests
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Edge cases covered
- [ ] All tests passing locally

## Type of Change

<!-- Select all that apply -->

- [ ] Bug fix (non-breaking change that fixes an issue)
- [ ] New feature (non-breaking change that adds functionality)
- [ ] Enhancement (improvement to existing functionality)
- [ ] Breaking change (fix or feature that changes existing behavior)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Security enhancement

## Breaking Changes

<!-- If this PR contains breaking changes, describe them and the migration path -->

N/A

## Test Plan

<!-- Describe how the changes were tested. Include specific commands and expected results -->

### Local Testing
1. Run: `pytest -v` (all tests should pass)
2. Run: `ruff check src tests` (no linting errors)
3. Run: `mypy src` (no type errors)
4. Run: `loom [command]` (verify functionality)

### Specific Testing Steps
- [ ] Step 1: [description]
- [ ] Step 2: [description]
- [ ] Step 3: [description]

### Test Coverage
- Current coverage: **X%** → New coverage: **Y%**
- Coverage report: [link to codecov or describe areas tested]

## Quality Checklist

- [ ] Code follows style guidelines (ruff, mypy, PEP 8)
- [ ] Self-review completed (logic is clear, no obvious bugs)
- [ ] Comments added for complex logic (especially in tools, scoring, pipelines)
- [ ] Documentation updated (docstrings, README, examples)
- [ ] No hardcoded secrets or sensitive data
- [ ] No new warnings or deprecated patterns introduced
- [ ] Type hints added to all new functions
- [ ] Tests cover all new code paths (80%+ target)
- [ ] CHANGELOG.md entry added
- [ ] No large/unnecessary dependencies added

## Performance Impact

<!-- Describe any performance changes, optimizations, or potential impacts -->

- Memory impact: None / Minimal / Significant
- Speed impact: None / Faster / Slower
- Details: [description]

## Security Review

<!-- Highlight any security-relevant changes -->

- [ ] No new security vulnerabilities introduced
- [ ] All user inputs validated
- [ ] No new hardcoded credentials
- [ ] SSRF checks in place (if applicable)
- [ ] Rate limiting considered (if applicable)
- [ ] Bandit security scan passes

## Dependencies

<!-- List any new or updated dependencies -->

- [ ] No new dependencies
- [ ] New dependencies: [list with justification]
- [ ] Updated dependencies: [list with version changes]

## Screenshots / Examples

<!-- If applicable, add screenshots or code examples demonstrating the changes -->

## Additional Context

<!-- Any additional information that reviewers should know -->

- **Tested on**: Python 3.11 / 3.12 / 3.13
- **Related PRs**: [link to related PRs if any]
- **Notes for reviewers**: [any specific areas to focus on]

## Reviewer Checklist

<!-- For reviewers to verify completeness -->

- [ ] Code changes make sense for the stated goals
- [ ] Tests adequately cover the changes
- [ ] No obvious bugs or edge cases missed
- [ ] Documentation is clear and complete
- [ ] Performance impact is acceptable
- [ ] Security guidelines followed
- [ ] No blocking concerns

---

Author: Ahmed Adel Bakr Alderai
