"""Validate the repository's Conventional Commit message policy."""

import re
import sys
from pathlib import Path

TYPES = "feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert"
HEADER = re.compile(rf"(?:{TYPES})(?:\([A-Za-z0-9_./-]+\))?!?: \S[^\r\n]*")


def validate(message: str) -> str | None:
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    if not lines or not HEADER.fullmatch(lines[0]):
        return "Use <type>[(scope)][!]: <description>, for example: feat(api): add task search"
    if len(lines) > 1 and lines[1].strip():
        return "Separate the commit header from the body with a blank line."
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_message.py COMMIT_MESSAGE_FILE", file=sys.stderr)
        return 2
    try:
        error = validate(Path(sys.argv[1]).read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        print(f"Cannot read commit message: {exc}", file=sys.stderr)
        return 2
    if error:
        print(f"Invalid Conventional Commit: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
