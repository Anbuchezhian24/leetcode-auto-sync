"""Main execution script for LeetCode to GitHub synchronization."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from src.git_manager import GitManager, GitError
from src.leetcode_client import LeetCodeClient, LeetCodeAuthError, LeetCodeAPIError
from src.solution_manager import SolutionManager, compute_code_hash
from src.state_manager import StateManager, make_problem_key
from src.submission_parser import SubmissionRecord, is_accepted_status

# Configure logging to console safely
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("leetcode-sync")


def load_config(config_path: str = "config.json") -> dict:
    """Load non-sensitive runtime configuration."""
    path = Path(config_path)
    if not path.exists():
        return {"solutions_directory": "solutions", "state_file": "leetcode-data.json", "submission_limit": 20}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"Could not read config file {config_path}: {e}. Using defaults.")
        return {"solutions_directory": "solutions", "state_file": "leetcode-data.json", "submission_limit": 20}


def run_sync(dry_run: bool = False, no_push: bool = False) -> None:
    """Execute main synchronization workflow."""
    # Load .env file for local development
    load_dotenv()

    if dry_run:
        mode_str = "(DRY RUN)"
    elif no_push:
        mode_str = "(NO PUSH)"
    else:
        mode_str = "(PRODUCTION)"

    logger.info(f"Starting LeetCode Sync Engine {mode_str}...")

    # Load configuration and state
    config = load_config()
    solutions_dir = config.get("solutions_directory", "solutions")
    state_file = config.get("state_file", "leetcode-data.json")
    limit = config.get("submission_limit", 20)

    state_mgr = StateManager(state_file=state_file)
    sol_mgr = SolutionManager(base_directory=solutions_dir)
    git_mgr = GitManager()

    client = LeetCodeClient()

    if not client.is_authenticated():
        logger.error("LeetCode authentication credentials are missing.")
        logger.error("Please set LEETCODE_SESSION and LEETCODE_CSRF_TOKEN environment variables.")
        sys.exit(1)

    logger.info("Authenticated credentials detected.")

    try:
        raw_submissions = client.fetch_recent_submissions(limit=limit)
    except (LeetCodeAuthError, LeetCodeAPIError) as e:
        logger.error(f"Failed to fetch submissions from LeetCode: {e}")
        sys.exit(1)

    if not raw_submissions:
        logger.info("No recent submissions retrieved from LeetCode.")
        return

    new_solutions_count = 0
    skipped_identical_count = 0
    skipped_existing_count = 0
    skipped_non_accepted_count = 0

    staged_files = []
    latest_commit_msg = ""

    for item in raw_submissions:
        sub_id = str(item.get("id") or "").strip()
        status_display = str(item.get("statusDisplay") or "").strip()

        if not sub_id:
            continue

        if not is_accepted_status(status_display):
            skipped_non_accepted_count += 1
            continue

        if state_mgr.is_submission_processed(sub_id):
            skipped_existing_count += 1
            continue

        # Fetch detailed submission info
        try:
            detail_data = client.fetch_submission_details(sub_id)
        except LeetCodeAPIError as e:
            logger.warning(f"Could not fetch details for submission {sub_id}: {e}")
            continue

        record = SubmissionRecord.from_dict(detail_data)
        if not record:
            logger.warning(f"Failed to parse submission details for submission ID {sub_id}.")
            continue

        problem_key = make_problem_key(record.problem_id, record.title_slug)
        code_hash = compute_code_hash(record.code)

        # Check for identical code hash duplicate
        matching_approach = state_mgr.get_matching_approach_for_hash(problem_key, code_hash)
        if matching_approach is not None:
            logger.info(
                f"Skipped identical solution for '{record.title}' "
                f"(Problem {record.problem_id}, matching Approach {matching_approach:02d})."
            )
            state_mgr.record_submission(
                submission_id=record.submission_id,
                problem_key=problem_key,
                approach_num=matching_approach,
                code_hash=code_hash,
                file_path="",
                timestamp=record.timestamp,
                is_duplicate=True,
            )
            skipped_identical_count += 1
            continue

        # Determine next approach number
        approach_num = state_mgr.get_next_approach_num(problem_key)
        rel_file_path = sol_mgr.get_solution_file_rel(record, approach_num)

        if dry_run:
            # Update in-memory state so subsequent submissions in this dry-run batch see this approach
            state_mgr.record_submission(
                submission_id=record.submission_id,
                problem_key=problem_key,
                approach_num=approach_num,
                code_hash=code_hash,
                file_path=str(rel_file_path),
                timestamp=record.timestamp,
                is_duplicate=False,
            )
            logger.info(
                f"[DRY RUN] Would create solution file for '{record.title}' "
                f"(Problem {record.problem_id}, Approach {approach_num:02d})."
            )
            new_solutions_count += 1
        else:
            # In production / no-push mode: solution file must be created successfully BEFORE state is updated
            try:
                sol_mgr.save_solution(record, approach_num)
            except Exception as e:
                logger.error(
                    f"Failed to create solution file for '{record.title}' (Submission {record.submission_id}): {e}"
                )
                continue

            state_mgr.record_submission(
                submission_id=record.submission_id,
                problem_key=problem_key,
                approach_num=approach_num,
                code_hash=code_hash,
                file_path=str(rel_file_path),
                timestamp=record.timestamp,
                is_duplicate=False,
            )
            logger.info(
                f"Saved new solution: {rel_file_path} (Problem {record.problem_id}, Approach {approach_num:02d})"
            )
            staged_files.append(str(rel_file_path))
            latest_commit_msg = f"LeetCode: Add {record.problem_id} - {record.title} (Approach {approach_num:02d})"
            new_solutions_count += 1

    # Save state file
    state_mgr.save_state(dry_run=dry_run)

    # Git Operations
    if not dry_run and not no_push and new_solutions_count > 0:
        staged_files.append(state_file)
        try:
            git_mgr.stage_files(staged_files)
            if new_solutions_count == 1:
                commit_msg = latest_commit_msg
            else:
                commit_msg = f"LeetCode: Sync {new_solutions_count} new accepted solutions"

            if git_mgr.commit(commit_msg):
                git_mgr.push()
        except GitError as e:
            logger.error(f"Git push failed: {e}")
            sys.exit(1)

    logger.info("-" * 40)
    logger.info(f"Sync complete {mode_str}.")
    logger.info(f"  New solutions synchronized : {new_solutions_count}")
    logger.info(f"  Skipped identical solutions: {skipped_identical_count}")
    logger.info(f"  Previously processed       : {skipped_existing_count}")
    logger.info(f"  Skipped non-accepted       : {skipped_non_accepted_count}")
    logger.info("-" * 40)


def main():
    parser = argparse.ArgumentParser(description="Synchronize LeetCode accepted solutions to GitHub.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate synchronization without creating files, modifying state, or pushing to Git.",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Fetch solutions, save solution files, and update state file, but skip Git commit and push.",
    )
    args = parser.parse_args()
    run_sync(dry_run=args.dry_run, no_push=args.no_push)


if __name__ == "__main__":
    main()
