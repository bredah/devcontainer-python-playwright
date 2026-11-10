import unittest

from security_reports import validate_inventory, validate_pins


class SecurityInventoryTests(unittest.TestCase):
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
