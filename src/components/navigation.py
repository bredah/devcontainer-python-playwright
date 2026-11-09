from playwright.sync_api import Page


class Navigation:
    def __init__(self, page: Page):
        self.page = page
        self.root = page.get_by_role("navigation")

    def go_to(self, name: str) -> None:
        self.root.get_by_role("link", name=name, exact=True).click()

    def back(self) -> None:
        self.page.go_back()

    def forward(self) -> None:
        self.page.go_forward()
