"""Git manager for staging, committing, and pushing solution and state updates."""

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Exception raised when a Git operation fails."""
    pass


class GitManager:
    """Handles repository checks, staging, committing, and pushing via Git CLI."""

    def __init__(self, repo_dir: Optional[str] = None):
        self.repo_dir = Path(repo_dir or ".").resolve()

    def _run_cmd(self, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run git subprocess safely."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=self.repo_dir,
                capture_output=True,
                text=True,
                check=check,
            )
            return res
        except subprocess.CalledProcessError as e:
            cmd_str = " ".join(args)
            err_msg = e.stderr.strip() if e.stderr else e.stdout.strip()
            logger.error(f"Git command 'git {cmd_str}' failed: {err_msg}")
            raise GitError(f"Git execution failed: {err_msg}")

    def configure_bot_user(self) -> None:
        """Configure GitHub Actions bot identity if user.name is not set."""
        try:
            name_check = self._run_cmd(["config", "user.name"], check=False)
            if not name_check.stdout.strip():
                logger.info("Setting Git user to github-actions[bot]")
                self._run_cmd(["config", "user.name", "github-actions[bot]"])
                self._run_cmd(
                    ["config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"]
                )
        except Exception as e:
            logger.warning(f"Could not configure Git bot user: {e}")

    def has_changes(self) -> bool:
        """Check if there are any staged or unstaged changes in the working tree."""
        res = self._run_cmd(["status", "--porcelain"])
        return bool(res.stdout.strip())

    def stage_files(self, paths: List[str]) -> None:
        """Stage specified paths using git add."""
        if not paths:
            return
        valid_paths = [p for p in paths if p]
        if valid_paths:
            self._run_cmd(["add"] + valid_paths)

    def commit(self, message: str, dry_run: bool = False) -> bool:
        """
        Commit staged changes with message.
        Returns True if commit succeeded, False if no changes to commit.
        """
        if dry_run:
            logger.info(f"[DRY RUN] Would commit: '{message}'")
            return True

        if not self.has_changes():
            logger.info("No changes detected. Skipping git commit.")
            return False

        self.configure_bot_user()
        self._run_cmd(["commit", "-m", message])
        logger.info(f"Committed changes: '{message}'")
        return True

    def push(self, dry_run: bool = False) -> None:
        """Push commits to remote repository."""
        if dry_run:
            logger.info("[DRY RUN] Would push commits to remote repository.")
            return

        logger.info("Pushing changes to remote GitHub repository...")
        self._run_cmd(["push"])
        logger.info("Successfully pushed changes to remote repository.")
