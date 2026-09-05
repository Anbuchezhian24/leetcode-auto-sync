"""Unit tests for single-run batch processing, approach numbering, duplicate skipping, and rollback safety."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.leetcode_client import LeetCodeClient
from src.solution_manager import SolutionManager
from src.state_manager import StateManager, make_problem_key
from src.submission_parser import SubmissionRecord
from sync import run_sync


class TestSyncFlow(unittest.TestCase):
    """Test suite verifying single-run batch state transitions and approach allocation."""

    def test_single_run_multiple_approaches_and_duplicate_skipping(self):
        sub1 = {
            "id": "10001",
            "code": "def findNumbers(nums):\n    return sum(len(str(x)) % 2 == 0 for x in nums)",
            "timestamp": 1700000000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "1295",
                "title": "Find Numbers with Even Number of Digits",
                "titleSlug": "find-numbers-with-even-number-of-digits",
                "difficulty": "Easy",
            },
        }

        sub2 = {
            "id": "10002",
            "code": "def findNumbers(nums):\n    res = 0\n    for n in nums:\n        if len(str(n)) % 2 == 0:\n            res += 1\n    return res",
            "timestamp": 1700001000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "1295",
                "title": "Find Numbers with Even Number of Digits",
                "titleSlug": "find-numbers-with-even-number-of-digits",
                "difficulty": "Easy",
            },
        }

        sub3 = {
            "id": "10003",
            "code": "def findNumbers(nums):\n    return sum(len(str(x)) % 2 == 0 for x in nums)",
            "timestamp": 1700002000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "1295",
                "title": "Find Numbers with Even Number of Digits",
                "titleSlug": "find-numbers-with-even-number-of-digits",
                "difficulty": "Easy",
            },
        }

        sub4 = {
            "id": "10004",
            "code": "class Solution:\n    def findNumbers(self, nums: list[int]) -> int:\n        return len([x for x in nums if len(str(x)) % 2 == 0])",
            "timestamp": 1700003000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "1295",
                "title": "Find Numbers with Even Number of Digits",
                "titleSlug": "find-numbers-with-even-number-of-digits",
                "difficulty": "Easy",
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "leetcode-data.json"
            state_mgr = StateManager(state_file=str(state_file))

            submissions = [sub1, sub2, sub3, sub4]
            records_processed = []
            problem_key = make_problem_key("1295", "find-numbers-with-even-number-of-digits")

            for sub_dict in submissions:
                rec = SubmissionRecord.from_dict(sub_dict)
                code_hash = rec.code  # mock code string as hash
                matching = state_mgr.get_matching_approach_for_hash(problem_key, code_hash)

                if matching is not None:
                    state_mgr.record_submission(
                        rec.submission_id, problem_key, matching, code_hash, "", rec.timestamp, is_duplicate=True
                    )
                    records_processed.append((rec.submission_id, "SKIP", matching))
                else:
                    app_num = state_mgr.get_next_approach_num(problem_key)
                    state_mgr.record_submission(
                        rec.submission_id, problem_key, app_num, code_hash, f"approach-{app_num:02d}.py", rec.timestamp, is_duplicate=False
                    )
                    records_processed.append((rec.submission_id, "APPROACH", app_num))

            self.assertEqual(records_processed[0], ("10001", "APPROACH", 1))
            self.assertEqual(records_processed[1], ("10002", "APPROACH", 2))
            self.assertEqual(records_processed[2], ("10003", "SKIP", 1))
            self.assertEqual(records_processed[3], ("10004", "APPROACH", 3))

    @patch("sync.LeetCodeClient")
    def test_run_sync_dry_run_batch_flow(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.fetch_recent_submissions.return_value = [
            {"id": "101", "statusDisplay": "Accepted"},
            {"id": "102", "statusDisplay": "Accepted"},
            {"id": "103", "statusDisplay": "Accepted"},
            {"id": "104", "statusDisplay": "Accepted"},
        ]

        def get_detail(sub_id):
            sub_id = str(sub_id)
            if sub_id == "101":
                code = "code_A"
            elif sub_id == "102":
                code = "code_B"
            elif sub_id == "103":
                code = "code_A"  # Duplicate of 101
            else:
                code = "code_C"

            return {
                "id": sub_id,
                "code": code,
                "timestamp": 1700000000,
                "statusDisplay": "Accepted",
                "lang": {"name": "python3"},
                "question": {
                    "questionFrontendId": "1295",
                    "title": "Find Numbers with Even Number of Digits",
                    "titleSlug": "find-numbers-with-even-number-of-digits",
                    "difficulty": "Easy",
                },
            }

        mock_client.fetch_submission_details.side_effect = get_detail
        mock_client_cls.return_value = mock_client

        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "leetcode-data.json"
            state_mgr = StateManager(state_file=str(state_file))

            with patch("sync.StateManager", return_value=state_mgr):
                run_sync(dry_run=True)

            # Check that in-memory state registered approaches 01, 02, and 03
            prob = state_mgr.data["problems"].get("1295-find-numbers-with-even-number-of-digits", {})
            approaches = prob.get("approaches", [])
            self.assertEqual(len(approaches), 3)
            self.assertEqual(approaches[0]["approach"], 1)
            self.assertEqual(approaches[1]["approach"], 2)
            self.assertEqual(approaches[2]["approach"], 3)

            # Verify that state file was NOT saved to disk because dry_run=True
            self.assertFalse(state_file.exists())

    @patch("sync.LeetCodeClient")
    @patch("sync.SolutionManager")
    def test_production_file_save_failure_rollback(self, mock_sol_mgr_cls, mock_client_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.fetch_recent_submissions.return_value = [
            {"id": "201", "statusDisplay": "Accepted"}
        ]
        mock_client.fetch_submission_details.return_value = {
            "id": "201",
            "code": "code_fail",
            "timestamp": 1700000000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "999",
                "title": "Failed File Problem",
                "titleSlug": "failed-file-problem",
                "difficulty": "Easy",
            },
        }
        mock_client_cls.return_value = mock_client

        mock_sol_mgr = MagicMock()
        mock_sol_mgr.get_solution_file_rel.return_value = Path("solutions/easy/0999-failed-file-problem/approach-01.py")
        mock_sol_mgr.save_solution.side_effect = OSError("Disk IO failure")
        mock_sol_mgr_cls.return_value = mock_sol_mgr

        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "leetcode-data.json"
            state_mgr = StateManager(state_file=str(state_file))

            with patch("sync.StateManager", return_value=state_mgr):
                run_sync(dry_run=False)

            # Submission 201 should NOT be recorded in state because save_solution raised an OSError
            self.assertFalse(state_mgr.is_submission_processed("201"))

    @patch("sync.GitManager")
    @patch("sync.LeetCodeClient")
    def test_run_sync_no_push_mode(self, mock_client_cls, mock_git_mgr_cls):
        mock_client = MagicMock()
        mock_client.is_authenticated.return_value = True
        mock_client.fetch_recent_submissions.return_value = [
            {"id": "301", "statusDisplay": "Accepted"}
        ]
        mock_client.fetch_submission_details.return_value = {
            "id": "301",
            "code": "print('no push test')",
            "timestamp": 1700000000,
            "statusDisplay": "Accepted",
            "lang": {"name": "python3"},
            "question": {
                "questionFrontendId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
            },
        }
        mock_client_cls.return_value = mock_client

        mock_git_mgr = MagicMock()
        mock_git_mgr_cls.return_value = mock_git_mgr

        with tempfile.TemporaryDirectory() as tmp_dir:
            state_file = Path(tmp_dir) / "leetcode-data.json"
            solutions_dir = Path(tmp_dir) / "solutions"

            with patch("sync.load_config", return_value={"solutions_directory": str(solutions_dir), "state_file": str(state_file), "submission_limit": 20}):
                run_sync(dry_run=False, no_push=True)

            # Solution file should be created
            saved_file = solutions_dir / "easy" / "0001-two-sum" / "approach-01.py"
            self.assertTrue(saved_file.exists())
            self.assertIn("print('no push test')", saved_file.read_text(encoding="utf-8"))

            # State file should be updated on disk
            self.assertTrue(state_file.exists())
            state_mgr = StateManager(state_file=str(state_file))
            self.assertTrue(state_mgr.is_submission_processed("301"))

            # Git commit and push MUST NOT be called
            mock_git_mgr.commit.assert_not_called()
            mock_git_mgr.push.assert_not_called()


if __name__ == "__main__":
    unittest.main()
