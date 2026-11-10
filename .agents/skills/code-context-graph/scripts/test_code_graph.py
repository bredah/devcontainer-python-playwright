import tempfile
import unittest
from pathlib import Path

from code_graph import query, refresh, search


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

    def test_search_code_docstrings_and_docs_with_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "src").mkdir()
            (root / "src" / "form.py").write_text(
                'def sendContact():\n    """Submit a contact form."""\n    pass\n'
            )
            (root / "README.md").write_text(
                "Jupyter authentication requires a private token.\n"
            )
            (root / ".env").write_text("SECRET=never_index_this_value\n")
            (root / "notes").mkdir()
            (root / "notes" / "private.ipynb").write_text(
                "never_index_notebook_outputs"
            )
            db, stats = refresh(root)
            self.assertEqual(stats["files"], 2)
            result = search(db, "where do we submit a contact form", 1)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["path"], "src/form.py")
            self.assertIn("Submit a contact", result[0]["snippet"])
            self.assertLessEqual(len(result[0]["snippet"]), 600)
            self.assertEqual(
                search(db, "Jupyter authentication", 3)[0]["path"], "README.md"
            )
            self.assertEqual(search(db, "never_index_this_value", 3), [])
            self.assertEqual(search(db, "never_index_notebook_outputs", 3), [])
            self.assertEqual(search(db, "where is the", 3), [])
            self.assertEqual(search(db, "contact", 3, "docs/"), [])
            self.assertTrue(search(db, "send contact", 3, "src/"))
            db.close()

    def test_text_index_refresh_removes_obsolete_results(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "README.md"
            path.write_text("Jupyter authentication token")
            db, _ = refresh(root)
            self.assertTrue(search(db, "authentication", 3))
            db.close()
            path.write_text("Browser navigation")
            db, stats = refresh(root)
            self.assertEqual(stats["reindexed"], 1)
            self.assertEqual(search(db, "authentication", 3), [])
            self.assertTrue(search(db, "navigation", 3))
            db.close()
            path.unlink()
            db, stats = refresh(root)
            self.assertEqual(stats["removed"], 1)
            self.assertEqual(search(db, "navigation", 3), [])
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
