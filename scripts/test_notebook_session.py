"""Regression checks for notebook target validation without a running browser."""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from notebooks.session import NotebookSession, check_target


class NotebookConnectionTests(unittest.TestCase):
    def test_unavailable_target_reports_demo_command(self):
        with patch("notebooks.session.socket.create_connection", side_effect=OSError):
            with self.assertRaisesRegex(ConnectionError, "make demo"):
                check_target("http://127.0.0.1:8765")

    def test_invalid_url(self):
        with self.assertRaisesRegex(ValueError, "absolute"):
            check_target("localhost:8765")

    def test_reachable_target(self):
        with patch("notebooks.session.socket.create_connection") as connect:
            check_target("https://example.com")
        connect.assert_called_once_with(("example.com", 443), timeout=3)

    def test_failed_start_cleans_up_worker(self):
        async def scenario():
            session = NotebookSession()
            with patch("notebooks.session.check_target", side_effect=ConnectionError):
                with self.assertRaises(ConnectionError):
                    await session._start("api", "http://127.0.0.1:8765")
            self.assertTrue(session._closed)
            await session.close()

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
