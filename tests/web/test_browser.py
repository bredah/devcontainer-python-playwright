from playwright.sync_api import Page, expect


def test_page_content(page: Page) -> None:
    page.set_content("<h1>Python + Playwright</h1><button>Continue</button>")

    expect(page.get_by_role("heading")).to_have_text("Python + Playwright")
    page.get_by_role("button", name="Continue").click()
