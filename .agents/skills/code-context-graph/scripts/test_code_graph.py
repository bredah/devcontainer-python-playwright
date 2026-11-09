import tempfile
import unittest
from pathlib import Path

from code_graph import query, refresh


class GraphTests(unittest.TestCase):
    def test_incremental_index_and_public_handles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            source = root / "src" / "form.py"
            source.write_text(
                'class Form:\n    def __init__(self, page):\n        self.status = page.get_by_role("status")\n    def fill(self, name: str = "Anna") -> None:\n        pass\n'
            )
            db, stats = refresh(root)
            self.assertEqual(stats["reindexed"], 1)
            self.assertIn(
                "status", query(db, "find", "Form.__init__", 10)[0]["attributes"]
            )
            self.assertIn(
                "name: str", query(db, "find", "Form.fill", 10)[0]["signature"]
            )
            db.close()
            db, stats = refresh(root)
            self.assertEqual(stats["reindexed"], 0)
            db.close()
            source.write_text("def changed():\n    Form()\n")
            db, stats = refresh(root)
            self.assertEqual(stats["reindexed"], 1)
            self.assertEqual(query(db, "find", "Form.fill", 10), [])
            self.assertEqual(query(db, "refs", "Form", 10)[0]["source"], "form.changed")
            db.close()
            source.unlink()
            db, stats = refresh(root)
            self.assertEqual(stats["removed"], 1)
            self.assertEqual(query(db, "refs", "Form", 10), [])
            db.close()

    def test_syntax_error_does_not_replace_previous_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "tests").mkdir()
            source = root / "tests" / "conftest.py"
            source.write_text(
                "@pytest.fixture\ndef app(page):\n    return DemoApp(page)\n"
            )
            db, _ = refresh(root)
            self.assertEqual(query(db, "find", "app", 10)[0]["kind"], "fixture")
            db.close()
            source.write_text("def broken(")
            with self.assertRaises(SyntaxError):
                refresh(root)
            source.write_text(
                "@pytest.fixture\ndef app(page):\n    return DemoApp(page)\n"
            )
            db, stats = refresh(root)
            self.assertEqual(stats["reindexed"], 0)
            self.assertTrue(query(db, "refs", "page", 10))
            db.close()


if __name__ == "__main__":
    unittest.main()
