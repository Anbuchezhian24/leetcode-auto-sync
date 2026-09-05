"""Unit tests for LeetCodeClient with mocked GraphQL responses."""

import unittest
from unittest.mock import MagicMock, patch
import requests

from src.leetcode_client import (
    LeetCodeAPIError,
    LeetCodeAuthError,
    LeetCodeClient,
)


class TestLeetCodeClient(unittest.TestCase):
    """Test suite verifying LeetCodeClient GraphQL query building, headers, and response handling."""

    def test_missing_credentials_fails_safely(self):
        client = LeetCodeClient(session_cookie="", csrf_token="")
        self.assertFalse(client.is_authenticated())
        with self.assertRaises(LeetCodeAuthError) as ctx:
            client.fetch_recent_submissions()
        self.assertIn("credentials are missing", str(ctx.exception))
        # Ensure secret tokens are not leaked in exception string
        self.assertNotIn("LEETCODE_SESSION=", str(ctx.exception))

    @patch("requests.Session.post")
    def test_fetch_recent_submissions_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "submissionList": {
                    "submissions": [
                        {
                            "id": "10000001",
                            "statusDisplay": "Accepted",
                            "lang": "python3",
                            "timestamp": "1700000000",
                            "title": "Two Sum",
                            "titleSlug": "two-sum",
                        },
                        {
                            "id": "10000002",
                            "statusDisplay": "Wrong Answer",
                            "lang": "cpp",
                            "timestamp": "1700000100",
                            "title": "Add Two Numbers",
                            "titleSlug": "add-two-numbers",
                        },
                    ]
                }
            }
        }
        mock_post.return_value = mock_response

        client = LeetCodeClient(session_cookie="fake_session", csrf_token="fake_csrf")
        subs = client.fetch_recent_submissions(limit=20)

        self.assertEqual(len(subs), 2)
        self.assertEqual(subs[0]["id"], "10000001")
        self.assertEqual(subs[0]["statusDisplay"], "Accepted")

        # Verify headers were passed correctly
        headers = mock_post.call_args[1]["headers"]
        self.assertIn("Cookie", headers)
        self.assertIn("x-csrftoken", headers)
        self.assertEqual(headers["x-csrftoken"], "fake_csrf")

    @patch("requests.Session.post")
    def test_fetch_submission_details_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "submissionDetails": {
                    "id": 10000001,
                    "code": "class Solution:\n    def twoSum(self, nums: List[int], target: int) -> List[int]:\n        return []",
                    "timestamp": 1700000000,
                    "statusDisplay": "Accepted",
                    "lang": {"name": "python3", "verboseName": "Python3"},
                    "question": {
                        "questionId": "1",
                        "questionFrontendId": "1",
                        "title": "Two Sum",
                        "titleSlug": "two-sum",
                        "difficulty": "Easy",
                    },
                }
            }
        }
        mock_post.return_value = mock_response

        client = LeetCodeClient(session_cookie="fake_session", csrf_token="fake_csrf")
        details = client.fetch_submission_details("10000001")

        self.assertEqual(details["id"], 10000001)
        self.assertIn("twoSum", details["code"])
        self.assertEqual(details["question"]["questionFrontendId"], "1")
        self.assertEqual(details["question"]["difficulty"], "Easy")

    @patch("requests.Session.post")
    def test_graphql_error_handling(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "errors": [{"message": "Invalid query format or permissions"}]
        }
        mock_post.return_value = mock_response

        client = LeetCodeClient(session_cookie="fake_session", csrf_token="fake_csrf")
        with self.assertRaises(LeetCodeAPIError) as ctx:
            client.fetch_recent_submissions()
        self.assertIn("Invalid query format or permissions", str(ctx.exception))

    @patch("requests.Session.post")
    def test_http_auth_error_handling(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        client = LeetCodeClient(session_cookie="fake_session", csrf_token="fake_csrf")
        with self.assertRaises(LeetCodeAuthError) as ctx:
            client.fetch_recent_submissions()
        self.assertIn("Session cookie or CSRF token may be expired", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
