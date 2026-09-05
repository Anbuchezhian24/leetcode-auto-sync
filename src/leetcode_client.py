"""LeetCode GraphQL API client supporting authenticated submission fetching."""

import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
DEFAULT_TIMEOUT = 15

# GraphQL Query strings
SUBMISSION_LIST_QUERY = """
query submissionList($offset: Int!, $limit: Int!) {
    submissionList(offset: $offset, limit: $limit) {
        submissions {
            id
            statusDisplay
            lang
            timestamp
            title
            titleSlug
        }
    }
}
"""

SUBMISSION_DETAILS_QUERY = """
query submissionDetails($submissionId: Int!) {
    submissionDetails(submissionId: $submissionId) {
        id
        code
        timestamp
        statusDisplay
        lang {
            name
            verboseName
        }
        question {
            questionId
            questionFrontendId
            title
            titleSlug
            difficulty
        }
    }
}
"""


class LeetCodeClientError(Exception):
    """Base exception for LeetCode client errors."""
    pass


class LeetCodeAuthError(LeetCodeClientError):
    """Exception raised when LeetCode credentials are missing or invalid."""
    pass


class LeetCodeAPIError(LeetCodeClientError):
    """Exception raised when LeetCode GraphQL request fails."""
    pass


class LeetCodeClient:
    """Client for fetching submission data from LeetCode GraphQL API."""

    def __init__(
        self,
        session_cookie: Optional[str] = None,
        csrf_token: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ):
        self.session_cookie = (session_cookie or os.getenv("LEETCODE_SESSION") or "").strip()
        self.csrf_token = (csrf_token or os.getenv("LEETCODE_CSRF_TOKEN") or "").strip()
        self.timeout = timeout
        self.session = requests.Session()

        if not self.session_cookie or not self.csrf_token:
            logger.error("LeetCode authentication credentials are missing.")

    def is_authenticated(self) -> bool:
        """Check if both LEETCODE_SESSION and LEETCODE_CSRF_TOKEN are present."""
        return bool(self.session_cookie and self.csrf_token)

    def _get_headers(self) -> Dict[str, str]:
        """Construct request headers with credentials safely included in Cookie header."""
        return {
            "Cookie": f"LEETCODE_SESSION={self.session_cookie}; csrftoken={self.csrf_token}",
            "x-csrftoken": self.csrf_token,
            "Referer": "https://leetcode.com",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json",
        }

    def _execute_graphql(
        self, query: str, variables: Dict[str, Any], max_retries: int = 2
    ) -> Dict[str, Any]:
        """
        Execute GraphQL query with retry handling and error checking.
        NEVER prints secret token values in logs or exception messages.
        """
        if not self.is_authenticated():
            raise LeetCodeAuthError(
                "LeetCode authentication credentials are missing. "
                "Please set LEETCODE_SESSION and LEETCODE_CSRF_TOKEN environment variables."
            )

        headers = self._get_headers()
        payload = {"query": query, "variables": variables}

        for attempt in range(max_retries + 1):
            try:
                response = self.session.post(
                    LEETCODE_GRAPHQL_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    logger.warning("LeetCode rate limit hit (429). Retrying after delay...")
                    time.sleep(2 * (attempt + 1))
                    continue

                if response.status_code in (401, 403):
                    raise LeetCodeAuthError(
                        "LeetCode authentication failed. Session cookie or CSRF token may be expired or invalid."
                    )

                response.raise_for_status()
                data = response.json()

                if "errors" in data and data["errors"]:
                    err_msg = data["errors"][0].get("message", "Unknown GraphQL error")
                    raise LeetCodeAPIError(f"GraphQL returned error: {err_msg}")

                return data.get("data", {})

            except (requests.Timeout, requests.ConnectionError) as e:
                logger.warning(f"Network error on attempt {attempt + 1}/{max_retries + 1}: {e}")
                if attempt == max_retries:
                    raise LeetCodeAPIError(f"Request failed after {max_retries + 1} attempts: {e}")
                time.sleep(1)
            except requests.HTTPError as e:
                raise LeetCodeAPIError(f"HTTP error: {e}")

        raise LeetCodeAPIError("Failed to execute GraphQL query.")

    def fetch_recent_submissions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch recent submission list from LeetCode.
        Returns raw submission list items.
        """
        logger.info(f"Fetching up to {limit} recent submissions...")
        data = self._execute_graphql(
            SUBMISSION_LIST_QUERY, {"offset": 0, "limit": limit}
        )

        sub_list_data = data.get("submissionList") or {}
        submissions = sub_list_data.get("submissions") or []
        if not isinstance(submissions, list):
            logger.warning("Received invalid submission list structure from GraphQL API.")
            return []

        logger.info(f"Retrieved {len(submissions)} submission records.")
        return submissions

    def fetch_submission_details(self, submission_id: str) -> Dict[str, Any]:
        """
        Fetch complete submission details (including code and question metadata) by submission ID.
        """
        try:
            sub_id_int = int(submission_id)
        except (ValueError, TypeError):
            raise LeetCodeAPIError(f"Invalid submission ID: {submission_id}")

        data = self._execute_graphql(
            SUBMISSION_DETAILS_QUERY, {"submissionId": sub_id_int}
        )
        details = data.get("submissionDetails") or {}
        if not isinstance(details, dict):
            raise LeetCodeAPIError(f"Submission details for ID {submission_id} were empty or invalid.")
        return details
