"""Run existing synchronous Playwright code from Jupyter's asyncio event loop."""

import asyncio
import os
import socket
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from api import TasksAPI
from components import DemoApp
from environment import load_environment


def check_target(base_url: str) -> None:
    """Fail before creating Playwright resources when the target is unavailable."""
    target = urlsplit(base_url)
    if target.scheme not in {"http", "https"} or not target.hostname:
        raise ValueError("BASE_URL must be an absolute http:// or https:// URL.")
    port = target.port or (443 if target.scheme == "https" else 80)
    try:
        with socket.create_connection((target.hostname, port), timeout=3):
            pass
    except OSError as error:
        raise ConnectionError(
            f"Cannot reach {target.hostname}:{port}. For the local examples, run "
            "`make demo` in another terminal inside the same devcontainer and "
            "keep it running. Then rerun the notebook setup. For another target, "
            "check BASE_URL and its network connectivity."
        ) from error


class NotebookSession:
    """Own all Playwright objects on one worker thread; return plain data to cells."""

    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._stack = ExitStack()
        self._target = None
        self._closed = False

    @classmethod
    async def api(cls, base_url: str):
        session = cls()
        await session._start("api", base_url)
        return session

    @classmethod
    async def web(cls, base_url: str):
        session = cls()
        await session._start("web", base_url)
        return session

    async def _start(self, mode, base_url):
        load_environment()

        def initialize():
            check_target(base_url)
            playwright = self._stack.enter_context(sync_playwright())
            if mode == "api":
                context = playwright.request.new_context(base_url=base_url)
                self._stack.callback(context.dispose)
                self._target = TasksAPI(context)
            else:
                endpoint = os.environ.get("PLAYWRIGHT_WS_ENDPOINT")
                browser = (
                    playwright.chromium.connect(endpoint, expose_network="<loopback>")
                    if endpoint
                    else playwright.chromium.launch(headless=True)
                )
                self._stack.callback(browser.close)
                context = browser.new_context()
                self._stack.callback(context.close)
                self._target = DemoApp(context.new_page(), base_url)

        try:
            await asyncio.get_running_loop().run_in_executor(self._executor, initialize)
        except BaseException:
            await self.close()
            raise

    async def run(self, action):
        """Execute a synchronous callback with TasksAPI or DemoApp on its owner thread.

        Convert responses/locators to dicts, lists, strings or bytes in the callback.
        Do not return live Playwright objects or use async callbacks.
        """
        if self._closed:
            raise RuntimeError("Notebook session is closed; create a new session.")
        return await asyncio.get_running_loop().run_in_executor(
            self._executor, lambda: action(self._target)
        )

    async def close(self):
        """Dispose contexts and stop Playwright; safe to call more than once."""
        if self._closed:
            return
        self._closed = True
        try:
            await asyncio.get_running_loop().run_in_executor(
                self._executor, self._stack.close
            )
        finally:
            self._executor.shutdown(wait=True)
