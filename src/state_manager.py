"""State manager for persisting LeetCode synchronization data in leetcode-data.json."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def make_problem_key(problem_id: str, title_slug: str) -> str:
    """Generate consistent problem key for state dictionary."""
    return f"{problem_id}-{title_slug}"


class StateManager:
    """Manages synchronization state loading, atomic writing, duplicate hash checks, and approach tracking."""

    def __init__(self, state_file: str = "leetcode-data.json"):
        self.state_file = Path(state_file)
        self.data: Dict[str, Any] = self.load_state()

    def load_state(self) -> Dict[str, Any]:
        """
        Load state from JSON file.
        Returns empty state structure if file doesn't exist or is corrupted.
        """
        empty_state: Dict[str, Any] = {"submissions": {}, "problems": {}}
        if not self.state_file.exists():
            logger.info(f"State file {self.state_file} does not exist. Initializing empty state.")
            return empty_state

        try:
            content = self.state_file.read_text(encoding="utf-8").strip()
            if not content:
                logger.info(f"State file {self.state_file} is empty. Initializing empty state.")
                return empty_state

            parsed = json.loads(content)
            if not isinstance(parsed, dict):
                logger.warning(f"State file {self.state_file} contained non-dict JSON. Resetting.")
                return empty_state

            parsed.setdefault("submissions", {})
            parsed.setdefault("problems", {})
            return parsed
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error reading state file {self.state_file}: {e}. Initializing empty state.")
            return empty_state

    def save_state(self, dry_run: bool = False) -> None:
        """
        Save state atomically to JSON file.
        Does not modify disk if dry_run is True.
        """
        if dry_run:
            logger.info("[DRY RUN] Skipping state file write.")
            return

        # Ensure correct structure
        self.data.setdefault("submissions", {})
        self.data.setdefault("problems", {})

        tmp_file = self.state_file.with_suffix(".json.tmp")
        try:
            content = json.dumps(self.data, indent=2, ensure_ascii=False)
            tmp_file.write_text(content, encoding="utf-8")
            tmp_file.replace(self.state_file)
            logger.info(f"Successfully saved state to {self.state_file}.")
        except Exception as e:
            logger.error(f"Failed to save state to {self.state_file}: {e}")
            if tmp_file.exists():
                tmp_file.unlink(missing_ok=True)
            raise

    def is_submission_processed(self, submission_id: str) -> bool:
        """Check if submission_id has already been synchronized."""
        submissions = self.data.get("submissions", {})
        return str(submission_id) in submissions

    def get_matching_approach_for_hash(self, problem_key: str, code_hash: str) -> Optional[int]:
        """
        Check if code_hash matches an existing approach for the given problem_key.
        Returns matching approach number if found, otherwise None.
        """
        problems = self.data.get("problems", {})
        problem_info = problems.get(problem_key)
        if not problem_info or not isinstance(problem_info, dict):
            return None

        approaches = problem_info.get("approaches", [])
        if not isinstance(approaches, list):
            return None

        for app in approaches:
            if isinstance(app, dict) and app.get("hash") == code_hash:
                return app.get("approach")
        return None

    def get_next_approach_num(self, problem_key: str) -> int:
        """Calculate next available approach number for a problem."""
        problems = self.data.get("problems", {})
        problem_info = problems.get(problem_key)
        if not problem_info or not isinstance(problem_info, dict):
            return 1

        approaches = problem_info.get("approaches", [])
        if not isinstance(approaches, list) or not approaches:
            return 1

        max_app = 0
        for app in approaches:
            if isinstance(app, dict):
                app_num = app.get("approach", 0)
                if isinstance(app_num, int) and app_num > max_app:
                    max_app = app_num
        return max_app + 1

    def record_submission(
        self,
        submission_id: str,
        problem_key: str,
        approach_num: int,
        code_hash: str,
        file_path: str,
        timestamp: int = 0,
        is_duplicate: bool = False,
    ) -> None:
        """Record submission details and approach mapping into state."""
        sub_id_str = str(submission_id)
        self.data.setdefault("submissions", {})
        self.data.setdefault("problems", {})

        # Record submission entry
        self.data["submissions"][sub_id_str] = {
            "problem_key": problem_key,
            "approach": approach_num,
            "hash": code_hash,
            "timestamp": timestamp,
            "is_duplicate": is_duplicate,
        }

        # Record problem approach entry if not duplicate file
        if not is_duplicate:
            problem_entry = self.data["problems"].setdefault(
                problem_key, {"approaches": []}
            )
            approaches = problem_entry.setdefault("approaches", [])

            # Verify approach doesn't already exist in array
            exists = any(
                isinstance(a, dict) and a.get("approach") == approach_num for a in approaches
            )
            if not exists:
                approaches.append(
                    {
                        "approach": approach_num,
                        "hash": code_hash,
                        "file_path": str(file_path),
                    }
                )
