import json
import tempfile
import unittest
from pathlib import Path

from aggregate_reports import aggregate


class ReportAggregationTests(unittest.TestCase):
    def write_suite(self, root, suite, failures=0, outcome="success"):
        folder = root / f"{suite}-results"
        folder.mkdir()
        (folder / "status.json").write_text(
            json.dumps({"TEST_OUTCOME": outcome, "BUILD_OUTCOME": "success"})
        )
        (folder / f"{suite}.xml").write_text(
            f'<testsuites><testsuite tests="2" failures="{failures}" errors="0" skipped="0"/></testsuites>'
        )
        (folder / f"{suite}.html").write_text("<html>Suite report</html>")

    def test_combines_three_suites_and_copies_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for suite in ("api", "web", "e2e"):
                self.write_suite(root, suite)
            output = root / "combined"
            self.assertEqual(aggregate(root, output, ["api", "web", "e2e"]), 0)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["totals"]["tests"], 6)
            self.assertEqual(len(summary["suites"]), 3)
            self.assertTrue((output / "e2e.html").exists())
            self.assertIn("e2e.html", (output / "index.html").read_text())

    def test_failed_and_missing_suites_do_not_hide_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_suite(root, "api", failures=1, outcome="failure")
            output = root / "combined"
            self.assertEqual(aggregate(root, output, ["api", "web"]), 1)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(
                [s["status"] for s in summary["suites"]], ["failed", "missing"]
            )
            self.assertEqual(summary["totals"]["failures"], 1)
            self.assertTrue((output / "summary.md").exists())

    def test_job_failure_and_malformed_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_suite(root, "api", outcome="failure")
            output = root / "combined"
            self.assertEqual(aggregate(root, output, ["api"]), 1)
            (root / "api-results" / "status.json").write_text("[]")
            self.assertEqual(aggregate(root, output, ["api"]), 1)
            summary = json.loads((output / "summary.json").read_text())
            self.assertEqual(summary["suites"][0]["status"], "missing")


if __name__ == "__main__":
    unittest.main()
