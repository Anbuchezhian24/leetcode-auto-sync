"""Unit tests for StateManager and state persistence."""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from src.state_manager import StateManager, make_problem_key


class TestStateManager(unittest.TestCase):
    """Test cases for state loading, lookup, saving, and approach tracking."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.state_file = Path(self.test_dir) / "leetcode-data.json"
        self.manager = StateManager(state_file=str(self.state_file))

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_empty_initial_state(self):
        self.assertEqual(self.manager.data, {"submissions": {}, "problems": {}})
        self.assertFalse(self.manager.is_submission_processed("1001"))

    def test_record_submission_and_approaches(self):
        problem_key = make_problem_key("0001", "two-sum")
        hash1 = "hash_code_1"

        # Record approach 1
        self.manager.record_submission(
            submission_id="1001",
            problem_key=problem_key,
            approach_num=1,
            code_hash=hash1,
            file_path="solutions/easy/0001-two-sum/approach-01.py",
            timestamp=1700000000,
        )

        self.assertTrue(self.manager.is_submission_processed("1001"))
        self.assertEqual(self.manager.get_matching_approach_for_hash(problem_key, hash1), 1)
        self.assertEqual(self.manager.get_next_approach_num(problem_key), 2)

        # Record approach 2 (different code)
        hash2 = "hash_code_2"
        self.manager.record_submission(
            submission_id="1002",
            problem_key=problem_key,
            approach_num=2,
            code_hash=hash2,
            file_path="solutions/easy/0001-two-sum/approach-02.py",
            timestamp=1700001000,
        )

        self.assertTrue(self.manager.is_submission_processed("1002"))
        self.assertEqual(self.manager.get_matching_approach_for_hash(problem_key, hash2), 2)
        self.assertEqual(self.manager.get_next_approach_num(problem_key), 3)

    def test_save_and_reload_state(self):
        problem_key = make_problem_key("0042", "trapping-rain-water")
        hash_code = "hash_rain_water"

        self.manager.record_submission(
            submission_id="2001",
            problem_key=problem_key,
            approach_num=1,
            code_hash=hash_code,
            file_path="solutions/hard/0042-trapping-rain-water/approach-01.py",
        )

        self.manager.save_state()
        self.assertTrue(self.state_file.exists())

        # Reload state with new manager instance
        reloaded = StateManager(state_file=str(self.state_file))
        self.assertTrue(reloaded.is_submission_processed("2001"))
        self.assertEqual(reloaded.get_matching_approach_for_hash(problem_key, hash_code), 1)

    def test_corrupted_state_file_recovery(self):
        # Write corrupted JSON to state file
        self.state_file.write_text("invalid json content {", encoding="utf-8")

        recovered_manager = StateManager(state_file=str(self.state_file))
        self.assertEqual(recovered_manager.data, {"submissions": {}, "problems": {}})


if __name__ == "__main__":
    unittest.main()
