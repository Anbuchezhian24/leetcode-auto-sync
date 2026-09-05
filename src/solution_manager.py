"""Solution file management, language mapping, code hashing, and path formatting."""

import hashlib
import re
from pathlib import Path
from typing import Dict, Tuple

from src.submission_parser import SubmissionRecord

# Language to extension mapping
LANGUAGE_EXTENSIONS: Dict[str, str] = {
    "python": ".py",
    "python3": ".py",
    "py": ".py",
    "cpp": ".cpp",
    "c++": ".cpp",
    "java": ".java",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "go": ".go",
    "golang": ".go",
    "rust": ".rs",
    "csharp": ".cs",
    "cs": ".cs",
    "c#": ".cs",
    "c": ".c",
    "kotlin": ".kt",
    "swift": ".swift",
    "php": ".php",
    "ruby": ".rb",
    "scala": ".scala",
    "sql": ".sql",
    "mysql": ".sql",
    "postgresql": ".sql",
    "oracle": ".sql",
    "ms_sql_server": ".sql",
}

# Comment style mapping based on extension
COMMENT_STYLES: Dict[str, str] = {
    ".py": "#",
    ".rb": "#",
    ".sql": "--",
}


def get_language_extension(language: str) -> str:
    """Get standard file extension for a LeetCode programming language."""
    clean_lang = str(language).strip().lower()
    return LANGUAGE_EXTENSIONS.get(clean_lang, ".txt")


def sanitize_slug(slug: str) -> str:
    """
    Sanitize slug to prevent path traversal and invalid filename characters.
    """
    clean = str(slug).strip().lower()
    # Replace spaces and underscores with hyphens
    clean = re.sub(r"[\s_]+", "-", clean)
    # Remove any character that is not alphanumeric or hyphen
    clean = re.sub(r"[^a-z0-9\-]", "", clean)
    # Collapse multiple hyphens
    clean = re.sub(r"-+", "-", clean).strip("-")
    return clean or "unnamed-problem"


def normalize_code(code: str) -> str:
    """
    Normalize source code for reliable duplicate hash calculation.
    - Standardizes line endings to LF (\n)
    - Strips trailing whitespace from each line
    - Strips leading/trailing blank lines
    - Ensures single trailing newline
    """
    if not code:
        return ""
    # Standardize line endings
    unified = code.replace("\r\n", "\n").replace("\r", "\n")
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in unified.split("\n")]
    # Strip leading empty lines
    while lines and not lines[0]:
        lines.pop(0)
    # Strip trailing empty lines
    while lines and not lines[-1]:
        lines.pop()
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def compute_code_hash(code: str) -> str:
    """Compute SHA-256 hash of normalized code."""
    normalized = normalize_code(code)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class SolutionManager:
    """Manages creation, directory routing, metadata header, and saving of solution files."""

    def __init__(self, base_directory: str = "solutions"):
        self.base_directory = Path(base_directory)

    def get_problem_directory_rel(self, difficulty: str, problem_id: str, title_slug: str) -> Path:
        """
        Build relative path to problem folder.
        Example: solutions/easy/0001-two-sum
        """
        clean_diff = str(difficulty).strip().lower()
        if clean_diff not in ("easy", "medium", "hard"):
            clean_diff = "easy"

        clean_slug = sanitize_slug(title_slug)
        folder_name = f"{problem_id}-{clean_slug}"
        return self.base_directory / clean_diff / folder_name

    def format_metadata_header(self, submission: SubmissionRecord, approach_num: int) -> str:
        """Generate metadata comment header for the solution file."""
        ext = get_language_extension(submission.language)
        comment_prefix = COMMENT_STYLES.get(ext, "//")

        header_lines = [
            f"{comment_prefix} LeetCode: {submission.title}",
            f"{comment_prefix} Problem ID: {submission.problem_id}",
            f"{comment_prefix} Difficulty: {submission.difficulty.capitalize()}",
            f"{comment_prefix} Language: {submission.language}",
            f"{comment_prefix} Approach: {approach_num:02d}",
            f"{comment_prefix} Submission ID: {submission.submission_id}",
            "",
        ]
        return "\n".join(header_lines)

    def get_solution_file_rel(self, submission: SubmissionRecord, approach_num: int) -> Path:
        """
        Build relative path to solution file.
        Example: solutions/easy/0001-two-sum/approach-01.py
        """
        rel_dir = self.get_problem_directory_rel(
            submission.difficulty, submission.problem_id, submission.title_slug
        )
        ext = get_language_extension(submission.language)
        filename = f"approach-{approach_num:02d}{ext}"
        return rel_dir / filename

    def save_solution(
        self, submission: SubmissionRecord, approach_num: int
    ) -> Tuple[Path, str]:
        """
        Generate and write solution file.
        Returns tuple of (relative_file_path, code_hash).
        """
        rel_file_path = self.get_solution_file_rel(submission, approach_num)
        header = self.format_metadata_header(submission, approach_num)
        raw_code = submission.code or ""
        full_content = header + raw_code

        # Write to disk
        target_path = rel_file_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(full_content, encoding="utf-8")

        code_hash = compute_code_hash(raw_code)
        return rel_file_path, code_hash
