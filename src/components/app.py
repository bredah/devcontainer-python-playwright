from playwright.sync_api import Page, Response

from .contact import ContactForm
from .navigation import Navigation
from .tasks import TaskList


class DemoApp:
    """Compose reusable UI components around a Playwright page."""

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url.rstrip("/")
        self.navigation = Navigation(page)
        self.contact = ContactForm(page)
        self.tasks = TaskList(page)
        self.heading = page.get_by_role("heading", level=1)

    def url(self, path: str = "/") -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def open(self, path: str = "/") -> Response | None:
        return self.page.goto(self.url(path))

    def open_tasks(self) -> Response:
        """Wait for the task API response as part of loading this view."""
        with self.page.expect_response("**/api/tasks") as response:
            self.open("/tasks")
        return response.value
