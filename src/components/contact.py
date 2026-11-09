from playwright.sync_api import Page


class ContactForm:
    def __init__(self, page: Page):
        self.name = page.get_by_label("Name", exact=True)
        self.email = page.get_by_label("Email")
        self.subject = page.get_by_label("Subject")
        self.terms = page.get_by_label("I accept the terms")
        self.submit_button = page.get_by_role("button", name="Send")
        self.status = page.get_by_role("status")

    def fill(
        self,
        *,
        name: str,
        email: str,
        subject: str = "Support",
        accept_terms: bool = True,
    ) -> None:
        self.name.fill(name)
        self.email.fill(email)
        self.subject.select_option(label=subject)
        self.terms.set_checked(accept_terms)

    def submit(self) -> None:
        self.submit_button.click()
