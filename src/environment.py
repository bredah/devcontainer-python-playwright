"""Load local configuration without overriding the existing process environment."""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    path = os.environ.get("DOTENV_PATH")
    default = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=Path(path) if path else default, override=False)
