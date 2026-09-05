"""Unit tests for solution manager, language extensions, and hashing."""

import shutil
import tempfile
import unittest
from pathlib import Path

from src.solution_manager import (
    SolutionManager,
    compute_code_hash,
    get_language_extension,
    normalize_code,
    sanitize_slug,
)
from src.submission_parser import SubmissionRecord


class TestSolutionManager(unittest.TestCase):
    """Test cases for SolutionManager functionality."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.manager = SolutionManager(base_directory=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_language_extensions(self):
        self.assertEqual(get_language_extension("python3"), ".py")
        self.assertEqual(get_language_extension("cpp"), ".cpp")
        self.assertEqual(get_language_extension("java"), ".java")
        self.assertEqual(get_language_extension("typescript"), ".ts")
        self.assertEqual(get_language_extension("go"), ".go")
        self.assertEqual(get_language_extension("rust"), ".rs")
        self.assertEqual(get_language_extension("unknown_lang"), ".txt")

    def test_sanitize_slug_and_path_traversal(self):
        self.assertEqual(sanitize_slug("two-sum"), "two-sum")
        self.assertEqual(sanitize_slug("../../etc/passwd"), "etcpasswd")
        self.assertEqual(sanitize_slug("valid anagram 123!"), "valid-anagram-123")
        self.assertEqual(sanitize_slug("---leading-trailing---"), "leading-trailing")

    def test_code_normalization_and_hashing(self):
        code1 = "def main():\r\n    print('hello')   \r\n\r\n"
        code2 = "def main():\n    print('hello')"

        norm1 = normalize_code(code1)
        norm2 = normalize_code(code2)
        self.assertEqual(norm1, norm2)

        hash1 = compute_code_hash(code1)
        hash2 = compute_code_hash(code2)
        self.assertEqual(hash1, hash2)

    def test_save_solution_file(self):
        record = SubmissionRecord(
            submission_id="99999",
            problem_id="0001",
            title="Two Sum",
            title_slug="two-sum",
            difficulty="easy",
            language="python3",
            code="print('two sum')",
            timestamp=1700000000,
            status_display="Accepted",
        )

        rel_path, code_hash = self.manager.save_solution(record, approach_num=1)
        full_path = Path(self.test_dir) / rel_path.relative_to("solutions") if str(rel_path).startswith("solutions") else Path(rel_path)

        self.assertTrue(full_path.exists())
        content = full_path.read_text(encoding="utf-8")
        self.assertIn("# LeetCode: Two Sum", content)
        self.assertIn("# Problem ID: 0001", content)
        self.assertIn("# Approach: 01", content)
        self.assertIn("print('two sum')", content)


if __name__ == "__main__":
    unittest.main()
