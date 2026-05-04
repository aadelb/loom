#!/usr/bin/env python3
"""
Automated UMMRO PR Workflow Script

Orchestrates PR creation process for UMMRO repository:
1. Creates feature branch in UMMRO repo
2. Copies specified files
3. Saves PR metadata record in loom/ummro_prs/
4. Guides user through commit/push/PR creation

Usage:
    ./scripts/ummro_pr.py "description of changes" file1 file2 ...
    ./scripts/ummro_pr.py --description "PR title" --files file1 file2 --dry-run

Example:
    ./scripts/ummro_pr.py "Add safety filter compliance checker" src/loom/tools/safety.py
"""

import argparse
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class UMMROPRWorkflow:
    """Manages UMMRO PR creation workflow."""

    def __init__(
        self,
        description: str,
        files: List[str],
        ummro_dir: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
    ):
        self.description = description
        self.files = files
        self.ummro_dir = Path(ummro_dir or os.path.expanduser("~/projects/ummro"))
        self.dry_run = dry_run
        self.verbose = verbose
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.branch_date = datetime.now().strftime("%Y%m%d")

        # Derived paths
        self.loom_root = Path(__file__).parent.parent
        self.ummro_prs_dir = self.loom_root / "ummro_prs"
        self.branch_name = self._sanitize_branch_name()
        self.branch = f"loom/{self.branch_date}-{self.branch_name}"

    def _sanitize_branch_name(self) -> str:
        """Sanitize description into valid git branch name."""
        sanitized = (
            self.description.lower()
            .replace(" ", "-")
            .replace("_", "-")
        )
        # Remove invalid characters
        import re
        sanitized = re.sub(r"[^a-z0-9-]", "", sanitized)
        # Remove consecutive hyphens
        sanitized = re.sub(r"-+", "-", sanitized)
        # Truncate to 40 chars
        return sanitized[:40].rstrip("-")

    def validate(self) -> bool:
        """Validate prerequisites."""
        errors = []

        if not self.ummro_dir.exists():
            errors.append(f"UMMRO repo not found at {self.ummro_dir}")

        for f in self.files:
            fpath = Path(f)
            if not fpath.exists():
                errors.append(f"File not found: {f}")

        if errors:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            return False

        return True

    def run(self) -> bool:
        """Execute workflow."""
        try:
            print("====== UMMRO PR Workflow ======")
            print(f"Timestamp: {self.timestamp}")
            print(f"Description: {self.description}")
            print(f"Branch: {self.branch}")
            print(f"Files: {len(self.files)} file(s)")
            if self.files:
                for f in self.files:
                    print(f"  - {f}")
            if self.dry_run:
                print("\n[DRY RUN MODE - No changes will be made]")
            print()

            # Step 1: Update UMMRO repo
            if not self._update_ummro_repo():
                return False

            # Step 2: Create branch
            if not self._create_branch():
                return False

            # Step 3: Copy files
            if not self._copy_files():
                return False

            # Step 4: Save PR metadata
            if not self._save_pr_metadata():
                return False

            # Step 5: Print summary
            self._print_summary()
            return True

        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return False

    def _update_ummro_repo(self) -> bool:
        """Update UMMRO repo main branch."""
        print("[1/4] Updating UMMRO repo...")
        try:
            if self.dry_run:
                print("  [DRY] Would update UMMRO repo")
                return True

            cwd = os.getcwd()
            os.chdir(self.ummro_dir)

            # Determine main branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
            )
            current = result.stdout.strip()

            # Switch to main/master
            for branch in ["main", "master"]:
                result = subprocess.run(
                    ["git", "checkout", branch],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    break

            subprocess.run(["git", "pull", "--quiet"], check=True)
            os.chdir(cwd)
            print("✓ UMMRO repo updated")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to update UMMRO repo: {e}", file=sys.stderr)
            return False

    def _create_branch(self) -> bool:
        """Create feature branch."""
        print(f"[2/4] Creating branch: {self.branch}")
        try:
            if self.dry_run:
                print(f"  [DRY] Would create branch: {self.branch}")
                return True

            cwd = os.getcwd()
            os.chdir(self.ummro_dir)
            subprocess.run(
                ["git", "checkout", "-b", self.branch],
                capture_output=True,
                check=True,
            )
            os.chdir(cwd)
            print("✓ Branch created")
            return True

        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create branch: {e}", file=sys.stderr)
            return False

    def _copy_files(self) -> bool:
        """Copy files to UMMRO repo."""
        if not self.files:
            print("[3/4] No files to copy (skipped)")
            return True

        print("[3/4] Copying files...")
        try:
            if self.dry_run:
                for f in self.files:
                    print(f"  [DRY] Would copy: {f}")
                return True

            for f in self.files:
                src = Path(f)
                dst = self.ummro_dir / src.name
                shutil.copy2(src, dst)
                print(f"  ✓ Copied: {src.name}")

            return True

        except Exception as e:
            print(f"✗ Failed to copy files: {e}", file=sys.stderr)
            return False

    def _save_pr_metadata(self) -> bool:
        """Save PR metadata record."""
        print("[4/4] Saving PR metadata...")
        try:
            if self.dry_run:
                print(f"  [DRY] Would save: {self.ummro_prs_dir}/{self.timestamp}_pr.md")
                return True

            self.ummro_prs_dir.mkdir(parents=True, exist_ok=True)
            pr_file = self.ummro_prs_dir / f"{self.timestamp}_pr.md"

            content = f"""# UMMRO PR Record

- **Description**: {self.description}
- **Created**: {self.timestamp}
- **Branch**: {self.branch}
- **Files Copied**: {len(self.files)}
"""

            if self.files:
                content += "\n## Files\n```\n"
                content += "\n".join(self.files)
                content += "\n```\n"

            content += """
## Status
- [ ] Files staged (git add)
- [ ] Changes committed (git commit)
- [ ] Branch pushed (git push -u origin BRANCH_NAME)
- [ ] PR created (gh pr create)

## Next Steps
1. Review changes in UMMRO working directory
2. Stage files: `git add .`
3. Commit: `git commit -m "description"`
4. Push: `git push -u origin {branch}`
5. Create PR: `gh pr create --title "title" --body "details"`
6. Update this file status once PR is created
""".format(branch=self.branch)

            with open(pr_file, "w") as f:
                f.write(content)

            print(f"✓ Saved: {pr_file}")
            return True

        except Exception as e:
            print(f"✗ Failed to save PR metadata: {e}", file=sys.stderr)
            return False

    def _print_summary(self) -> None:
        """Print workflow summary and next steps."""
        print()
        print("====== Summary ======")
        print(f"UMMRO working directory: {self.ummro_dir}")
        print(f"Current branch: {self.branch}")
        print(f"PR record saved: {self.ummro_prs_dir}/{self.timestamp}_pr.md")
        print()
        print("Next steps:")
        print(f"  1. cd {self.ummro_dir}")
        print(f"  2. Review changes: git diff main")
        print(f"  3. Stage files: git add .")
        print(f"  4. Commit: git commit -m '{self.description}'")
        print(f"  5. Push: git push -u origin {self.branch}")
        print(f"  6. Create PR: gh pr create")
        print(f"  7. Update PR record when done")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated UMMRO PR workflow script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Add safety compliance tool" src/loom/tools/safety.py
  %(prog)s --description "Update docs" --files docs/api.md --dry-run
  %(prog)s --ummro-dir ~/projects/ummro-fork "Feature PR" file1 file2
        """,
    )

    parser.add_argument(
        "description",
        nargs="?",
        default=None,
        help="PR description/title",
    )
    parser.add_argument(
        "files",
        nargs="*",
        default=[],
        help="Files to copy to UMMRO repo",
    )
    parser.add_argument(
        "--description",
        "-d",
        dest="desc_flag",
        help="PR description (alternative to positional arg)",
    )
    parser.add_argument(
        "--files",
        "-f",
        nargs="+",
        dest="files_flag",
        default=[],
        help="Files to copy (alternative to positional args)",
    )
    parser.add_argument(
        "--ummro-dir",
        default=None,
        help="Path to UMMRO repo (default: ~/projects/ummro)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Determine description and files
    description = args.desc_flag or args.description
    files = args.files_flag or args.files

    # Validate inputs
    if not description:
        parser.print_help()
        print("\nERROR: Description required", file=sys.stderr)
        return 1

    # Create and run workflow
    workflow = UMMROPRWorkflow(
        description=description,
        files=files,
        ummro_dir=args.ummro_dir,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if not workflow.validate():
        return 1

    if workflow.run():
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
