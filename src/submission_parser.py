"""Submission parser and data model for LeetCode submissions."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


def normalize_problem_id(problem_id: Any) -> str:
    """
    Normalize problem ID to consistent string format with padding.

    Examples:
        1 -> "0001"
        42 -> "0042"
        1295 -> "1295"
        10001 -> "10001"
    """
    if problem_id is None:
        return "0000"

    raw_str = str(problem_id).strip()
    if not raw_str:
        return "0000"
    if raw_str.isdigit():
        return raw_str.zfill(max(4, len(raw_str)))
    return raw_str


def is_accepted_status(status: Optional[str]) -> bool:
    """Check if submission status display represents an accepted solution."""
    if not status:
        return False
    normalized = str(status).strip().lower()
    return normalized in ("accepted", "a_10")


@dataclass
class SubmissionRecord:
    """Dataclass representing a parsed LeetCode submission."""

    submission_id: str
    problem_id: str
    title: str
    title_slug: str
    difficulty: str
    language: str
    code: str
    timestamp: int
    status_display: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Optional["SubmissionRecord"]:
        """
        Safely construct a SubmissionRecord from dictionary payload.
        Returns None if required fields are missing or malformed.
        """
        if not isinstance(data, dict):
            return None

        # Extract submission ID
        submission_id = str(data.get("id") or data.get("submission_id") or "").strip()
        if not submission_id:
            return None

        # Extract status
        status_display = str(
            data.get("statusDisplay") or data.get("status_display") or ""
        ).strip()
        if not is_accepted_status(status_display):
            return None

        # Extract question metadata
        question_data = data.get("question") or {}
        if not isinstance(question_data, dict):
            question_data = {}

        raw_problem_id = (
            question_data.get("questionFrontendId")
            or question_data.get("questionId")
            or data.get("question_id")
            or data.get("problem_id")
            or ""
        )
        problem_id = normalize_problem_id(raw_problem_id)

        title = str(
            question_data.get("title") or data.get("title") or "Unknown Problem"
        ).strip()

        title_slug = str(
            question_data.get("titleSlug")
            or data.get("titleSlug")
            or data.get("title_slug")
            or ""
        ).strip()
        if not title_slug and title:
            # Fallback title_slug generation
            title_slug = title.lower().replace(" ", "-")

        raw_difficulty = str(
            question_data.get("difficulty") or data.get("difficulty") or "Easy"
        ).strip()
        difficulty = raw_difficulty.lower()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "easy"

        # Extract language
        lang_data = data.get("lang")
        if isinstance(lang_data, dict):
            language = str(lang_data.get("name") or lang_data.get("verboseName") or "python3").strip()
        else:
            language = str(lang_data or data.get("language") or "python3").strip()

        code = data.get("code") or ""
        if not isinstance(code, str):
            code = str(code)

        try:
            timestamp = int(data.get("timestamp") or 0)
        except (ValueError, TypeError):
            timestamp = 0

        return cls(
            submission_id=submission_id,
            problem_id=problem_id,
            title=title,
            title_slug=title_slug,
            difficulty=difficulty,
            language=language,
            code=code,
            timestamp=timestamp,
            status_display=status_display,
        )
