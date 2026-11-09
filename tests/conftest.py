import os
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest
from playwright.sync_api import APIRequestContext, Page, Playwright
from tests.mock.demo_app import DemoHandler

from api import TasksAPI
from components import DemoApp
from environment import load_environment

load_environment()


@pytest.fixture(scope="session")
def connect_options():
    endpoint = os.environ.get("PLAYWRIGHT_WS_ENDPOINT")
    # Forward browser localhost traffic to the Python client in the devcontainer.
    return {"endpoint": endpoint, "expose_network": "<loopback>"} if endpoint else None


@pytest.fixture
def demo_url():
    """Start an isolated demo server for each test; no external services needed."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
    server.tasks = {}
    server.next_id = 1
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


@pytest.fixture
def api(playwright: Playwright, demo_url: str):
    """APIRequestContext runs HTTP requests without launching a browser."""
    context = playwright.request.new_context(base_url=demo_url)
    try:
        yield context
    finally:
        context.dispose()


@pytest.fixture
def tasks_api(api: APIRequestContext) -> TasksAPI:
    return TasksAPI(api)


@pytest.fixture
def app(page: Page, demo_url: str) -> DemoApp:
    return DemoApp(page, demo_url)
