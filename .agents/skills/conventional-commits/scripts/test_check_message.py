import unittest

from check_message import validate


class CommitMessageTests(unittest.TestCase):
    def test_valid_messages(self):
        for message in (
            "feat: add API notebooks",
            "fix(api): validate empty tasks",
            "refactor(web)!: replace form interface",
            "feat!: remove legacy endpoint\n\nBREAKING CHANGE: use /api/tasks instead",
            "docs: update setup\n\nExplain the notebook workflow.\n\nRefs: #12",
            "chore: update hooks\n\n# Git comment",
        ):
            with self.subTest(message=message):
                self.assertIsNone(validate(message))

    def test_invalid_messages(self):
        for message in (
            "",
            "update files",
            "feat: ",
            "feat:    ",
            "feat:add tasks",
            "unknown: add tasks",
            "feat(): add tasks",
            "fix(api): add tasks\nNo separator",
            "Merge branch main",
            'Revert "previous commit"',
            "fixup! feat: add tasks",
        ):
            with self.subTest(message=message):
                self.assertIsNotNone(validate(message))


if __name__ == "__main__":
    unittest.main()
