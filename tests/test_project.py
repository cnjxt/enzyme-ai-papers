from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProjectWorkflowTest(unittest.TestCase):
    def run_script(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_validate_script_passes(self) -> None:
        result = self.run_script("scripts/validate_papers.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Validation passed.", result.stdout)

    def test_build_docs_script_generates_expected_pages(self) -> None:
        result = self.run_script("scripts/build_docs.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        expected_paths = [
            ROOT / "README.md",
            ROOT / "docs" / "index.md",
            ROOT / "docs" / "archive.md",
            ROOT / "docs" / "info.md",
            ROOT / "docs" / "assets" / "site.css",
            ROOT / "docs" / "assets" / "app.js",
        ]
        for path in expected_paths:
            self.assertTrue(path.exists(), f"Missing generated page: {path}")
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.strip(), f"Generated file is empty: {path}")

        index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
        info = (ROOT / "docs" / "info.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Pick of the Week", index)
        self.assertIn("paper-submit-form", info)
        self.assertIn("Open GitHub Submission", info)
        self.assertIn("Enzyme AI Papers Weekly", readme)
        self.assertRegex(readme, r"2026-W17.*2026\.4\.20-")
        self.assertNotIn("Pick of the Week", readme)
        self.assertNotIn("Directly published paper for enzyme AI curation", readme)
        self.assertNotIn("project owner URL workflow", index)
        self.assertIn("- Links: [Paper]", readme)
        self.assertIn("MORE_INFO.md", readme)

    def test_fetch_candidates_is_safe_placeholder(self) -> None:
        result = self.run_script("scripts/fetch_candidates.py")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("disabled", result.stdout)

    def test_preview_issue_accepts_url_only_submission(self) -> None:
        event = {
            "issue": {
                "number": 42,
                "title": "[Paper]: Example enzyme paper",
                "body": "### Paper URL\n\nhttps://doi.org/10.1234/example.paper\n\n### Why this paper matters\n\n_No response_",
                "labels": [{"name": "needs-review"}],
                "user": {"login": "submitter"},
            },
            "sender": {"login": "maintainer"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            result = self.run_script("scripts/preview_issue.py", "--event", str(event_path))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Paper suggestion preview", result.stdout)
        self.assertIn("https://doi.org/10.1234/example.paper", result.stdout)
        self.assertIn("`accepted`", result.stdout)

    def test_accept_issue_ignores_unaccepted_issue(self) -> None:
        event = {
            "issue": {
                "number": 43,
                "title": "[Paper]: Example enzyme paper",
                "body": "### Paper URL\n\nhttps://example.org/paper",
                "labels": [{"name": "needs-review"}],
                "user": {"login": "submitter"},
            },
            "sender": {"login": "maintainer"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            result = self.run_script("scripts/accept_issue.py", "--event", str(event_path))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not labeled accepted", result.stdout)

    def test_preview_issue_rejects_local_urls(self) -> None:
        event = {
            "issue": {
                "number": 44,
                "title": "[Paper]: Local URL",
                "body": "### Paper URL\n\nhttp://127.0.0.1:8000/paper",
                "labels": [{"name": "needs-review"}],
                "user": {"login": "submitter"},
            },
            "sender": {"login": "maintainer"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            result = self.run_script("scripts/preview_issue.py", "--event", str(event_path))

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("not a public web URL", result.stdout)

    def test_accept_issue_rejects_local_urls(self) -> None:
        event = {
            "issue": {
                "number": 45,
                "title": "[Paper]: Local URL",
                "body": "### Paper URL\n\nhttp://localhost/paper",
                "labels": [{"name": "accepted"}],
                "user": {"login": "submitter"},
            },
            "sender": {"login": "maintainer"},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            event_path = Path(tmpdir) / "event.json"
            event_path.write_text(json.dumps(event), encoding="utf-8")
            result = self.run_script("scripts/accept_issue.py", "--event", str(event_path))

        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("public paper URL", result.stderr)

    def test_publish_url_dry_run_generates_paper_yaml(self) -> None:
        result = self.run_script(
            "scripts/publish_url.py",
            "--url",
            "https://doi.org/10.1234/direct.publish.example",
            "--title",
            "Direct Publish Example Paper",
            "--note",
            "Demonstrates owner-only direct URL publishing.",
            "--tags",
            "enzyme design, benchmark",
            "--reviewer",
            "maintainer",
            "--accepted-at",
            "2026-04-26T00:00:00+00:00",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("id: doi-10-1234-direct-publish-example", result.stdout)
        self.assertIn("title: Direct Publish Example Paper", result.stdout)
        self.assertIn("curator: maintainer", result.stdout)
        self.assertIn("featured: false", result.stdout)
        self.assertIn("https://doi.org/10.1234/direct.publish.example", result.stdout)

    def test_manage_paper_dry_run_updates_seed_metadata(self) -> None:
        result = self.run_script(
            "scripts/manage_paper.py",
            "--selector",
            "2026-example-enzyme-plm",
            "--one-liner",
            "Updated direct management summary.",
            "--featured",
            "false",
            "--reviewer",
            "maintainer",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("id: 2026-example-enzyme-plm", result.stdout)
        self.assertIn("one_liner: Updated direct management summary.", result.stdout)
        self.assertIn("featured: false", result.stdout)

    def test_manage_paper_dry_run_can_select_by_url_for_delete(self) -> None:
        result = self.run_script(
            "scripts/manage_paper.py",
            "--selector",
            "https://example.org/example-enzyme-language-model-paper",
            "--delete",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Would delete paper: 2026-example-enzyme-plm", result.stdout)


if __name__ == "__main__":
    unittest.main()
