# PyPI Trusted Publishing Setup for Loom

## Why Trusted Publishing

PyPI **trusted publishing** uses OIDC (OpenID Connect) tokens to authenticate package uploads, eliminating the need for long-lived API tokens. Instead of storing a secret API key, you configure a trusted relationship between PyPI and GitHub Actions: when a workflow runs in your repository, it requests a short-lived token from GitHub, which PyPI validates and honors.

This approach is:
- **More secure**: No API tokens to rotate or leak
- **Audit-friendly**: Each upload is tied to a specific GitHub workflow and commit
- **EU AI Act compliant**: Transparent token provenance for compliance testing

As of 2026, PyPI recommends trusted publishing for all new projects. For detailed official documentation, see [PyPI Trusted Publishers](https://docs.pypi.org/trusted-publishers/).

## Prerequisites Checklist

- [ ] **PyPI account** created and verified at https://pypi.org
- [ ] **Email verified** on your PyPI account
- [ ] **2FA enabled** on your PyPI account (TOTP or security key; required for publishing)
- [ ] **GitHub repository** created (ours: `github.com/aadelb/loom`)
- [ ] **Release workflow** exists at `.github/workflows/release.yml` and uses `environment: pypi`
- [ ] **GitHub `pypi` environment** configured on your repo (confirm with `gh api repos/aadelb/loom/environments --jq '.environments[].name'`)

## PyPI Configuration (Step-by-Step)

### 1. Log in to PyPI
Navigate to https://pypi.org/account/login/ and sign in with your credentials.

### 2. Open Publisher Settings
Go to https://pypi.org/manage/account/publishing/

### 3. Locate the "Add Pending Publisher" Section
Scroll down to the section labeled **"Add a new pending publisher"**. You should see a form with four fields.

### 4. Fill in the Publisher Details

| Field | Value |
|-------|-------|
| **PyPI Project Name** | `loom-mcp` |
| **Owner** | `aadelb` |
| **Repository name** | `loom` |
| **Workflow name** | `release.yml` |
| **Environment name** | `pypi` |

**Copy these values exactly.** The workflow name must match the filename in `.github/workflows/` (without the `.yml` extension for the dropdown, but the file must be `release.yml`).

### 5. Click "Add"
After submission, you should see a confirmation message. The publisher will appear in the **"Pending trusted publishers"** table on the same page.

### 6. Verification
Once added, any workflow run that:
- Pushes a tag matching `v*`
- Runs `release.yml`
- Uses the `pypi` GitHub environment
- Requests an OIDC token

will be trusted to publish to `loom-mcp` on PyPI.

## GitHub Configuration (Verify Only)

The `pypi` environment should already be configured on your repository. To verify:

```bash
gh api repos/aadelb/loom/environments --jq '.environments[].name'
```

Expected output should include `pypi`.

If the environment is missing, create it:

```bash
gh api --method PUT repos/aadelb/loom/environments/pypi
```

No deployment branches or protection rules are required for PyPI publishing (they are used for environment-specific review gates, which we don't need).

## Cutting the Tag and Publishing

Follow this sequence to tag and publish `v0.1.0-alpha.1`:

```bash
cd /Users/aadel/projects/loom

# Step 1: Final sanity checks
PYTHONPATH=src python3 -m pytest tests/ --no-cov -q
# Expected: 168 passed / 5 skipped

PYTHONPATH=src python3 -m mypy src/loom
# Expected: 0 errors

PYTHONPATH=src python3 -m ruff check src/loom
# Expected: All checks passed

# Step 2: Create annotated tag (load release notes from prepared file)
git tag -a v0.1.0-alpha.1 -F release-notes/v0.1.0-alpha.1.md

# Step 3: Review the tag
git show v0.1.0-alpha.1 --stat

# Step 4: Push the tag to GitHub (triggers release.yml)
git push origin v0.1.0-alpha.1

# Step 5: Watch workflows
gh run list --limit 5
gh run watch
```

The `release.yml` workflow will:
1. Check out the tagged commit
2. Build the package (`python -m build`)
3. Use trusted publishing to upload to PyPI
4. Create a GitHub Release with auto-generated notes and build artifacts

## Verification After Publishing

Once the workflow completes, verify publication with:

### PyPI
```bash
pip index versions loom-mcp
# Expected: includes "0.1.0a1"
```

### GitHub Release
```bash
gh release view v0.1.0-alpha.1
# Expected: release notes and dist/* files attached
```

## Troubleshooting

### Error: "pending publisher not configured"
**Problem**: The trusted publisher entry is missing from PyPI.  
**Fix**: Follow **Section 4 (PyPI Configuration)** again. Ensure all four fields match exactly, then click "Add".

### Error: "environment 'pypi' does not exist"
**Problem**: The GitHub `pypi` environment is not configured on your repository.  
**Fix**: Run:
```bash
gh api --method PUT repos/aadelb/loom/environments/pypi
```

Then retry the tag push.

### Error: "file already exists"
**Problem**: The version `0.1.0a1` is already published to PyPI.  
**Fix**: Either:
1. Yank the release at `https://pypi.org/project/loom-mcp/#history`, then re-upload
2. Bump to `0.1.0a2` and tag/push that instead

Once yanked, the file slot can be reused within 24 hours.

### Workflow fails with auth error
**Problem**: The OIDC token exchange failed.  
**Cause**: The trusted publisher entry does not match your workflow. Double-check:
- PyPI Project Name is exactly `loom-mcp`
- Owner is exactly `aadelb`
- Repository name is exactly `loom`
- Workflow name is exactly `release.yml` (no `.yml` extension in the field)
- Environment name is exactly `pypi`

**Fix**: Delete the pending publisher from PyPI (via https://pypi.org/manage/account/publishing/) and add a new one with corrected details.

## What Happens When You Push the Tag

1. **GitHub detects** the `v0.1.0-alpha.1` tag
2. **Workflow triggers**: `.github/workflows/release.yml` runs
3. **Build phase**: `python -m build` creates `dist/loom-mcp-0.1.0a1.tar.gz` and `.whl`
4. **Publish phase**: The `pypa/gh-action-pypi-publish` action:
   - Requests a short-lived OIDC token from GitHub
   - Submits the token to PyPI
   - PyPI validates token against the trusted publisher config
   - If valid, publishes the package
5. **Release phase**: Softprops' `action-gh-release` creates a GitHub Release
6. **Done**: `pip install loom-mcp==0.1.0a1` works

All three phases are fully automated. You just push the tag and watch.
