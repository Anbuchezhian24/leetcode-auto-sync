"""Unit tests for submission parser and normalization logic."""

import unittest
from src.submission_parser import SubmissionRecord, normalize_problem_id, is_accepted_status


class TestSubmissionParser(unittest.TestCase):
    """Test cases for SubmissionRecord and problem ID normalization."""

    def test_normalize_problem_id(self):
        self.assertEqual(normalize_problem_id(1), "0001")
        self.assertEqual(normalize_problem_id("42"), "0042")
        self.assertEqual(normalize_problem_id(1295), "1295")
        self.assertEqual(normalize_problem_id("10001"), "10001")
        self.assertEqual(normalize_problem_id(None), "0000")
        self.assertEqual(normalize_problem_id("LCP 01"), "LCP 01")

    def test_is_accepted_status(self):
        self.assertTrue(is_accepted_status("Accepted"))
        self.assertTrue(is_accepted_status("ACCEPTED"))
        self.assertTrue(is_accepted_status("A_10"))
        self.assertFalse(is_accepted_status("Wrong Answer"))
        self.assertFalse(is_accepted_status("Time Limit Exceeded"))
        self.assertFalse(is_accepted_status("Runtime Error"))
        self.assertFalse(is_accepted_status(None))

    def test_parse_accepted_submission(self):
        raw_data = {
            "id": "123456",
            "statusDisplay": "Accepted",
            "timestamp": 1700000000,
            "code": "class Solution:\n    def twoSum(self, nums, target):\n        pass",
            "lang": {"name": "python3", "verboseName": "Python3"},
            "question": {
                "questionId": "1",
                "title": "Two Sum",
                "titleSlug": "two-sum",
                "difficulty": "Easy",
            },
        }

        record = SubmissionRecord.from_dict(raw_data)
        self.assertIsNotNone(record)
        self.assertEqual(record.submission_id, "123456")
        self.assertEqual(record.problem_id, "0001")
        self.assertEqual(record.title, "Two Sum")
        self.assertEqual(record.title_slug, "two-sum")
        self.assertEqual(record.difficulty, "easy")
        self.assertEqual(record.language, "python3")
        self.assertEqual(record.status_display, "Accepted")

    def test_parse_rejected_submission(self):
        raw_data = {
            "id": "123457",
            "statusDisplay": "Wrong Answer",
            "question": {"questionId": "1", "title": "Two Sum"},
        }
        record = SubmissionRecord.from_dict(raw_data)
        self.assertIsNone(record)

    def test_parse_missing_fields(self):
        raw_data = {
            "id": "123458",
            "statusDisplay": "Accepted",
        }
        record = SubmissionRecord.from_dict(raw_data)
        self.assertIsNotNone(record)
        self.assertEqual(record.submission_id, "123458")
        self.assertEqual(record.problem_id, "0000")
        self.assertEqual(record.title, "Unknown Problem")
        self.assertEqual(record.difficulty, "easy")
        self.assertEqual(record.language, "python3")


if __name__ == "__main__":
    unittest.main()
