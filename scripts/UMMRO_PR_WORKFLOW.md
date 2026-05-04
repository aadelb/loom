# UMMRO PR Workflow Scripts

Automated scripts to streamline PR creation for the UMMRO repository.

## Overview

When working on UMMRO-related changes:
1. Use either the bash or Python script to set up the PR workflow
2. Scripts create feature branch in UMMRO repo
3. Scripts copy specified files from loom to UMMRO
4. Scripts save PR metadata record in `loom/ummro_prs/`
5. User manually stages, commits, pushes, and creates PR

## Scripts

### Bash Version: `ummro_pr.sh`

Lightweight bash implementation for quick PR setup.

```bash
./scripts/ummro_pr.sh "description of changes" [file1] [file2] ...
```

**Example:**
```bash
./scripts/ummro_pr.sh "Add safety compliance checker" src/loom/tools/safety.py
```

**Features:**
- Fast execution
- Minimal dependencies (bash, git)
- Clear step-by-step feedback
- ANSI status indicators (✓, ⚠)

### Python Version: `ummro_pr.py`

Feature-rich Python implementation with comprehensive argument parsing.

```bash
./scripts/ummro_pr.py "description" [file1] [file2] ...
./scripts/ummro_pr.py --description "desc" --files file1 file2
./scripts/ummro_pr.py --dry-run "test pr" file.txt
```

**Examples:**
```bash
# Positional arguments
./scripts/ummro_pr.py "Add compliance tool" src/loom/tools/compliance.py

# Explicit flags
./scripts/ummro_pr.py -d "Update API docs" -f docs/api.md docs/examples.md

# Dry-run mode (no changes made)
./scripts/ummro_pr.py --dry-run "Test PR" myfile.txt

# Custom UMMRO location
./scripts/ummro_pr.py --ummro-dir ~/projects/ummro-fork "PR title" file1

# Verbose output
./scripts/ummro_pr.py -v "Add feature" file1.py file2.py
```

**Features:**
- Flexible argument parsing (positional or named)
- Dry-run mode for testing
- Verbose output option
- Type hints and comprehensive error handling
- Class-based architecture for extensibility

## Workflow Steps

### 1. Run Script (Bash or Python)

```bash
cd /Users/aadel/projects/loom

# Using bash
./scripts/ummro_pr.sh "Add new feature" src/loom/tools/feature.py

# OR using Python
./scripts/ummro_pr.py "Add new feature" src/loom/tools/feature.py
```

### 2. Script Execution Flow

The script will:
1. Validate UMMRO repo exists at `~/projects/ummro`
2. Update main branch in UMMRO repo
3. Create feature branch: `loom/YYYYMMDD-description-name`
4. Copy specified files to UMMRO repo
5. Save PR metadata record to `loom/ummro_prs/YYYYMMDD_HHMMSS_pr.md`

### 3. Manual Git Steps (in UMMRO repo)

```bash
cd ~/projects/ummro

# Review changes
git diff main

# Stage all changes
git add .

# Commit with descriptive message
git commit -m "Add new feature description"

# Push to remote
git push -u origin loom/YYYYMMDD-description-name

# Create PR using GitHub CLI
gh pr create --title "Your PR Title" --body "Detailed description"
```

### 4. Update PR Metadata

After PR is created:
```bash
# Edit the PR metadata file saved by script
nano loom/ummro_prs/YYYYMMDD_HHMMSS_pr.md

# Check boxes as steps are completed
# Add PR URL when created
```

## Output Files

### PR Metadata Records

Location: `/Users/aadel/projects/loom/ummro_prs/`

Each PR creates a markdown file with:
- Description
- Branch name
- Files copied
- Workflow checklist
- Next steps

Example filename: `20260504_205826_pr.md`

## Configuration

Both scripts respect:
- **UMMRO_DIR** environment variable: Path to UMMRO repo (default: `~/projects/ummro`)
- **LOOM_ROOT**: Automatically resolved to scripts parent directory

## Error Handling

Scripts validate:
- UMMRO repo exists at specified location
- All specified files exist
- Git operations succeed
- Directories are writable

### Common Issues

| Issue | Solution |
|-------|----------|
| UMMRO repo not found | Set `--ummro-dir` flag or ensure `~/projects/ummro` exists |
| Files not found | Use absolute paths or verify file locations |
| Git branch exists | Delete old branch: `git branch -D loom/old-branch` |
| Permission denied | Run `chmod +x scripts/ummro_pr.sh scripts/ummro_pr.py` |

## Dry-Run Mode

Test the workflow without making changes:

```bash
# Python only - test what would happen
./scripts/ummro_pr.py --dry-run "Test PR" file.txt
```

Output shows all planned actions without executing them.

## Best Practices

1. **Use descriptive PR titles**
   ```bash
   # Good
   ./scripts/ummro_pr.py "Add compliance check for AI Act Article 15"
   
   # Less useful
   ./scripts/ummro_pr.py "Update stuff"
   ```

2. **Group related files**
   ```bash
   # Good - related to one feature
   ./scripts/ummro_pr.py "Add compliance pipeline" tool1.py tool2.py tool3.py
   
   # Less focused - unrelated files
   ./scripts/ummro_pr.py "Random updates" file1.py file2.py file3.py
   ```

3. **Review before committing**
   ```bash
   cd ~/projects/ummro
   git diff main          # Always review changes
   git diff main --stat   # See summary
   ```

4. **Keep metadata updated**
   - Check boxes as workflow progresses
   - Add PR URL after creation
   - Save as reference

5. **One feature per branch**
   - Use separate branches for unrelated changes
   - Makes review easier
   - Simplifies reverting if needed

## Integration with CI/CD

After PR is created:
- GitHub Actions will run linting, testing, type checking
- Address any failing checks before merge
- Require review from UMMRO maintainers
- Update metadata when PR is merged

## Script Comparison

| Feature | Bash | Python |
|---------|------|--------|
| Speed | Very fast | Fast |
| Dependencies | bash, git | Python 3.7+ |
| Argument parsing | Positional only | Positional + named |
| Dry-run mode | No | Yes |
| Error handling | Basic | Comprehensive |
| Type hints | N/A | Full coverage |
| Extensibility | Limited | Class-based |

Choose bash for quick operations, Python for testing or complex scenarios.

## Troubleshooting

### Check script permissions
```bash
ls -l scripts/ummro_pr.{sh,py}
# Should show: -rwxr-xr-x
```

### Test scripts without side effects
```bash
# Python dry-run
./scripts/ummro_pr.py --dry-run "Test" file.txt

# Bash with set -x for debugging
bash -x ./scripts/ummro_pr.sh "Test" file.txt
```

### Verify UMMRO repo setup
```bash
ls -la ~/projects/ummro/.git
git -C ~/projects/ummro status
git -C ~/projects/ummro branch -a
```

### Check PR records
```bash
ls -la loom/ummro_prs/
cat loom/ummro_prs/LATEST_TIMESTAMP_pr.md
```

## Support

For issues or improvements to the scripts:
1. Test with `--dry-run` mode (Python only)
2. Check script permissions
3. Verify UMMRO repo is properly cloned
4. Review error messages carefully
