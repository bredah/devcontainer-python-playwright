import unittest

from security_reports import validate_inventory, validate_pins
from security_summary import render_summary


class SecurityInventoryTests(unittest.TestCase):
    def test_human_summary_with_and_without_findings(self):
        lock = {
            "package": [{"name": "example", "version": "1.0.0", "groups": ["main"]}]
        }
        manifest = {"project": {"dependencies": ["example (==1.0.0)"]}}
        metadata = {
            "generated_at_utc": "2026-01-01T00:00:00Z",
            "scope": "all groups",
            "packages": 1,
            "sarif_findings": 0,
            "scanner_image": "scanner:1",
            "lock_sha256": "abc",
        }
        report = render_summary(lock, manifest, {"runs": [{"results": []}]}, metadata)
        self.assertIn("No vulnerability findings", report)
        self.assertIn("| example | 1.0.0 | main | Direct |", report)
        metadata["sarif_findings"] = 1
        sarif = {
            "runs": [
                {
                    "results": [
                        {
                            "ruleId": "CVE-example",
                            "level": "error",
                            "message": {
                                "text": "Update | package\n<script>unsafe</script>"
                            },
                        }
                    ]
                }
            ]
        }
        report = render_summary(lock, manifest, sarif, metadata)
        self.assertIn("CVE-example", report)
        self.assertIn("error: 1", report)
        self.assertIn("&#124;", report)
        self.assertNotIn("<script>", report)

    def test_direct_pins_match_lock_and_ranges_are_rejected(self):
        lock = {"package": [{"name": "example", "version": "1.0.0"}]}
        for requirement in ("example (>=1.0)", "example (==2.0.0)", "example (==1.*)"):
            with self.subTest(requirement=requirement):
                with self.assertRaises(ValueError):
                    validate_pins({"project": {"dependencies": [requirement]}}, lock)
        validate_pins({"project": {"dependencies": ["example (==1.0.0)"]}}, lock)

    def test_full_inventory_and_normalized_names(self):
        lock = {"package": [{"name": "example_lib", "version": "1.0.0"}]}
        sbom = {"components": [{"name": "example-lib", "version": "1.0.0"}]}
        self.assertEqual(validate_inventory(lock, sbom), 1)

    def test_missing_or_wrong_versions_fail(self):
        lock = {"package": [{"name": "example", "version": "1.0.0"}]}
        for components in ([], [{"name": "example", "version": "2.0.0"}]):
            with self.subTest(components=components):
                with self.assertRaisesRegex(ValueError, "missing locked packages"):
                    validate_inventory(lock, {"components": components})


if __name__ == "__main__":
    unittest.main()
