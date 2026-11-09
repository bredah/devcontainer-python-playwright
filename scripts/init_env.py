"""Initialize a private local environment file without displaying credentials."""

import os
import re
import secrets
from pathlib import Path


def main():
    path = Path(os.environ.get("PROJECT_ENV_FILE", ".env"))
    content = path.read_text() if path.exists() else Path(".env.example").read_text()
    pattern = re.compile(r"^(?:export\s+)?JUPYTER_TOKEN=.*$", re.MULTILINE)
    match = pattern.search(content)
    if not match or not match[0].split("=", 1)[1].strip().strip("\"'"):
        assignment = f"JUPYTER_TOKEN={secrets.token_hex(32)}"
        content = (
            pattern.sub(assignment, content)
            if match
            else content.rstrip() + "\n" + assignment + "\n"
        )
    # Create with private permissions before writing a token.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        os.fchmod(file.fileno(), 0o600)
        file.write(content)
    print("Local environment initialized with a private Jupyter token (not displayed).")


if __name__ == "__main__":
    main()
