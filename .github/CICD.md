# Loom CI/CD Pipeline Documentation

## Overview

The Loom MCP server uses a comprehensive GitHub Actions CI/CD pipeline with:
- **Continuous Integration (CI)**: Automated testing, linting, security scanning on every push/PR
- **Continuous Deployment (CD)**: Manual deployment to staging/production on Hetzner
- **Safety Gates**: Multiple quality checkpoints before deployment

## CI Pipeline (`.github/workflows/ci.yml`)

### Stages

The CI pipeline runs automatically on push to `main` or `develop`, and on all pull requests.

#### 1. **Pre-Flight Checks** (runs first)
- Validates YAML syntax in workflow files
- Checks commit message format (conventional commits)
- Ensures no critical configuration issues

**Status**: Must pass before any other jobs run

#### 2. **Lint & Type Check**
- **Ruff linter**: Code style and quality checks
  ```bash
  ruff check src tests --output-format=github
  ```
- **Ruff formatter**: Code formatting verification
  ```bash
  ruff format --check src tests
  ```
- **MyPy**: Static type checking
  ```bash
  mypy src --junit-xml=/tmp/mypy-junit.xml
  ```

**Requirements**:
- All code must pass ruff linting
- Code must follow PEP 8 style guidelines
- All functions must have type hints
- Type errors must be resolved

#### 3. **Test Suite** (matrix: Python 3.11, 3.12, 3.13)
- Runs against 3 Python versions in parallel
- Unit and integration tests
- Code coverage measurement
- Journey/E2E tests with mocked fixtures

**Coverage Requirements**:
- Minimum **80%** code coverage
- Coverage report uploaded to Codecov
- Failures block merge

**Test Command**:
```bash
pytest tests/ \
  -v \
  --timeout=300 \
  --maxfail=5 \
  -m "not live" \
  --cov=src/loom \
  --cov-report=xml
```

#### 4. **Journey/E2E Tests** (Mocked)
- Starts Loom MCP server locally
- Runs comprehensive journey tests
- Uses mocked fixtures (no live API calls)
- Tests critical user workflows

#### 5. **Security Scan**
- **Bandit**: Python security analysis
  - Scans for HIGH severity issues (blocking)
  - Warns on MEDIUM severity issues (non-blocking)
  - Looks for common vulnerabilities (hardcoded secrets, SQL injection, etc.)

**Security Checks**:
- No hardcoded credentials
- SSRF URL validation
- Secure API key handling
- Safe subprocess usage

#### 6. **Build**
- Builds Python wheel and source distribution
- Validates package contents
- Uploads artifacts for deployment

### CI Status Indicators

Check the status of CI on:
- GitHub PR: "Checks" tab shows status of each job
- GitHub Actions: `.github/workflows/` tab shows full pipeline
- Codecov: Coverage badge in README (requires codecov/codecov-action)

### CI Artifacts

Jobs produce artifacts:
- `test-results-py3.11`, `py3.12`, `py3.13`: JUnit XML test reports
- `type-check-results`: MyPy type checking results
- `security-bandit-report`: Bandit security scan JSON
- `dist`: Built Python packages (wheel + sdist)

Artifacts retained for **7 days**, then auto-deleted.

### Caching Strategy

The pipeline uses GitHub Actions caching to speed up builds:

```
Key: ${{ runner.os }}-pip-{stage}-v1-${{ hashFiles('**/pyproject.toml') }}
```

Benefits:
- First run builds cache (full pip install)
- Subsequent runs restore from cache
- Cache invalidates only if `pyproject.toml` changes
- Reduces build time by 60-80%

## Deploy Pipeline (`.github/workflows/deploy.yml`)

### Deployment Trigger

Manual trigger via GitHub Actions UI:

```
Actions → Deploy to Hetzner → Run workflow
```

Select deployment options:
- **Target**: `staging` or `production` (required)
- **Skip Tests**: (not recommended, default: false)
- **Dry Run**: Plan without executing changes (default: false)

### Deployment Stages

#### 1. **Pre-Flight Validation**
- Generates unique deployment ID: `YYYYMMDD_HHMMSS-{short-sha}`
- Validates Hetzner secrets configured
- Confirms valid target environment
- Creates deployment record

#### 2. **Tests** (optional, conditional)
Skipped if `skip_tests: true` (not recommended)

```bash
pytest tests/ --timeout=300 --maxfail=3 -m "not live"
```

#### 3. **Security Check**
- Runs Bandit security scan
- Fails if HIGH severity issues found
- Pre-deployment security verification

#### 4. **Build Package**
- Builds wheel distribution
- Uploads to workflow artifacts
- Ready for deployment

#### 5. **Deploy to Target**
Deployment steps:

1. **Setup SSH**: Configure secure connection to Hetzner
2. **Create directories**: Prepare release structure
   ```
   /opt/loom/
   ├── releases/YYYYMMDD_HHMMSS-{sha}/
   ├── backups/
   ├── logs/
   ├── data/
   └── current → releases/YYYYMMDD_HHMMSS-{sha}/
   ```
3. **Backup current**: Copy existing installation to backup
4. **Upload package**: rsync wheel and dependencies
5. **Install dependencies**: Create venv and install package
6. **Pre-deploy checks**: Verify installation
7. **Switch release**: Update `current` symlink
8. **Restart service**: Reload systemd service

#### 6. **Health Check**
- SSH health check: Verify server initialization
- HTTP health check: Check `/health` endpoint (may not be available internally)
- Retries: 15 attempts, 2-second intervals

#### 7. **Rollback** (on failure)
If health check fails:
- Detects most recent backup
- Restores from backup
- Restarts service
- Full automatic rollback

#### 8. **Notifications**
- Creates deployment summary in GitHub Actions
- Records deployment metadata
- Logs deployment ID and status

### Deployment Directory Structure

```
/opt/loom/
├── current → releases/20250504_145830-a1b2c3d/  [symlink]
├── releases/
│   ├── 20250504_145830-a1b2c3d/  [new deployment]
│   │   ├── dist/
│   │   │   ├── loom-mcp-0.1.0.whl
│   │   │   └── loom-mcp-0.1.0.tar.gz
│   │   ├── venv/  [virtual environment]
│   │   └── ...
│   └── 20250504_140000-z9y8x7w/  [old deployment]
├── backups/
│   └── backup_20250504_135530/  [pre-deploy backup]
├── logs/  [application logs]
└── data/  [persistent data]
```

### Deployment Workflow

```
User triggers manual deployment
        ↓
Pre-flight validation
        ↓
Test (if enabled)
        ↓
Security check
        ↓
Build package
        ↓
Deploy to target
        ├─→ Backup current
        ├─→ Upload package
        ├─→ Install dependencies
        ├─→ Switch symlink
        └─→ Restart service
        ↓
Health check
        ├─→ SUCCESS: Deployment complete
        └─→ FAILURE: Automatic rollback
```

## GitHub Secrets Configuration

Required GitHub Secrets for deployment:

```
HETZNER_HOST       = hetzner.example.com      [SSH hostname]
HETZNER_USER       = deploy_user              [SSH username]
HETZNER_SSH_KEY    = [private key contents]   [SSH private key]
```

### Setting Up Secrets

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Add each secret:
   - `HETZNER_HOST`
   - `HETZNER_USER`
   - `HETZNER_SSH_KEY`

### SSH Key Setup

Generate SSH key on Hetzner (if not already present):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/deploy_key -N ""
cat ~/.ssh/deploy_key.pub >> ~/.ssh/authorized_keys
```

Add to GitHub Secrets:

```bash
cat ~/.ssh/deploy_key | base64 -w 0  # Copy output
```

## Code Owners and Review

See `.github/CODEOWNERS` for review requirements by area:

- Core infrastructure (`server.py`, `config.py`, etc.): @aadelb
- Tools and providers: @aadelb
- Tests and CI/CD: @aadelb
- Documentation: @aadelb

All PRs require review from code owners before merge.

## Pull Request Process

1. **Create feature branch**: `git checkout -b feature/my-feature`
2. **Make changes**: Implement feature with tests
3. **Push to GitHub**: `git push -u origin feature/my-feature`
4. **Create PR**: GitHub will show PR template
5. **Fill PR template**: Complete all sections
6. **CI runs automatically**: Watch for check results
7. **Review**: Code owners review changes
8. **Address feedback**: Make requested changes
9. **Merge**: Once approved and CI passes

### PR Checklist

From `.github/pull_request_template.md`:

- [ ] Code follows style guidelines (ruff, mypy)
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests cover the changes
- [ ] CHANGELOG.md entry added

## Common Tasks

### Running Tests Locally

```bash
# All tests
pytest -v

# Specific test file
pytest tests/test_tools/test_fetch.py -v

# With coverage
pytest --cov=src/loom --cov-report=html

# Skip slow tests
pytest -m "not slow"

# Run only on Hetzner (for heavy tests)
ssh hetzner "cd /path && pytest tests/"
```

### Running Linter Locally

```bash
# Check code style
ruff check src tests

# Auto-fix style issues
ruff check --fix src tests

# Format code
ruff format src tests

# Type check
mypy src
```

### Manual Deployment

1. Go to **Actions → Deploy to Hetzner**
2. Click **Run workflow**
3. Select options:
   - Target: `staging` or `production`
   - Skip Tests: Leave unchecked
   - Dry Run: Check to preview
4. Click **Run workflow**
5. Monitor in Actions tab
6. Check deployment summary when complete

### Rollback After Deployment

If deployment fails and automatic rollback didn't work:

```bash
ssh hetzner@hetzner.example.com << 'EOF'
cd /opt/loom
LATEST_BACKUP=$(ls -t backups/ | head -1)
rm -f current
cp -r backups/$LATEST_BACKUP current
systemctl restart loom
echo "Rolled back to: $LATEST_BACKUP"
EOF
```

### View Deployment History

```bash
ssh hetzner@hetzner.example.com << 'EOF'
cd /opt/loom
echo "=== Releases ==="
ls -ltr releases/ | tail -5
echo "=== Backups ==="
ls -ltr backups/ | tail -5
echo "=== Current ==="
readlink -f current
EOF
```

## Monitoring and Debugging

### CI Job Failures

1. **Check the job logs**:
   - Go to GitHub Actions → Failed workflow
   - Click the failed job
   - Scroll down to see error details

2. **Common failures**:
   - **Linting errors**: Run `ruff check --fix src tests` locally
   - **Test failures**: Run `pytest -v` locally to reproduce
   - **Type errors**: Run `mypy src` locally to fix
   - **Coverage**: Add tests to increase coverage

3. **Get detailed logs**:
   - Each job shows full stdout/stderr
   - Expand collapsed steps
   - Check artifact uploads

### Deployment Failures

1. **Check deployment logs**:
   - Go to Actions → Deploy to Hetzner → Failed run
   - Expand each job to see errors

2. **Common issues**:
   - **SSH connection fails**: Verify secrets are set correctly
   - **Health check fails**: SSH to Hetzner and check service status
   - **Package installation fails**: Check dependency compatibility
   - **Service restart fails**: Check systemd status

3. **Debug on Hetzner**:
   ```bash
   ssh hetzner@hetzner.example.com
   cd /opt/loom/current
   source venv/bin/activate
   python -c "import loom; print(loom.__version__)"
   systemctl status loom --user
   journalctl --user -u loom -n 50
   ```

## Performance Optimization

### CI Pipeline Performance

- **Caching**: pip cache reduces install time by ~5 minutes
- **Parallel jobs**: Tests run on Python 3.11/3.12/3.13 in parallel
- **Job dependencies**: Jobs run sequentially only when needed
- **Matrix strategy**: Multi-version testing without duplication

### Deployment Performance

- **Incremental install**: Only installs changed dependencies
- **Symlink switching**: Atomic deployment (no downtime)
- **Background service**: Service restart doesn't block pipeline
- **Backup efficiency**: Only keeps last 5 backups to save space

## Best Practices

### Code Changes

- Write tests first (TDD)
- Keep commits atomic and focused
- Use conventional commit messages
- Fill PR template completely
- Respond to review feedback promptly

### CI/CD Discipline

- Don't skip tests (they catch bugs early)
- Monitor coverage (aim for 80%+)
- Address security findings promptly
- Review deployment logs before and after
- Keep deployment windows short

### Security

- Never commit secrets (use GitHub Secrets)
- Validate all user inputs
- Use parameterized queries
- Scan dependencies regularly
- Review Bandit findings

## Troubleshooting

### "Deployment failed: SSH key not found"

Solution: Verify `HETZNER_SSH_KEY` secret is set correctly

```bash
gh secret list | grep HETZNER
```

### "Health check failed after 30 attempts"

Solution: Service may not have started. Check on Hetzner:

```bash
ssh hetzner
cd /opt/loom/current
systemctl status loom --user
journalctl --user -u loom -f
```

### "Coverage below threshold"

Solution: Add more test coverage

```bash
pytest --cov=src/loom --cov-report=html
# Open htmlcov/index.html to see uncovered lines
```

### "Tests passing locally but failing in CI"

Possible causes:
- Environment differences (check Python version)
- Missing test fixture (check conftest.py)
- Race condition (use pytest-asyncio markers)
- Network test hitting live endpoints (mark with @pytest.mark.live)

## References

- GitHub Actions Documentation: https://docs.github.com/en/actions
- Conventional Commits: https://www.conventionalcommits.org/
- Python Testing: pytest documentation in `docs/`
- Deployment Guide: See `deploy/README.md`
