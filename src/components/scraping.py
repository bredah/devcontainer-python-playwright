from playwright.sync_api import Page


def extract_links(page: Page) -> list[dict[str, str]]:
    """Return link text and absolute URLs as plain data for notebooks or tests."""
    return page.get_by_role("link").evaluate_all(
        "links => links.map(link => ({text: link.textContent.trim(), url: link.href}))"
    )
