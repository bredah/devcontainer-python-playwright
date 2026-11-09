from playwright.sync_api import Page


class TaskList:
    def __init__(self, page: Page):
        self.page = page
        self.root = page.get_by_role("list", name="Task list")
        self.items = self.root.get_by_role("listitem")

    def mock_response(self, tasks: list[dict[str, str]]) -> None:
        """Register before navigation; only this page's requests are intercepted."""
        self.page.route("**/api/tasks", lambda route: route.fulfill(json=tasks))
