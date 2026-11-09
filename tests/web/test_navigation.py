from playwright.sync_api import expect

from components import DemoApp


def test_navigation_and_history(app: DemoApp):
    app.open()
    expect(app.page).to_have_title("Playwright Demo")
    expect(app.heading).to_have_text("Example application")

    app.navigation.go_to("Contact")
    expect(app.page).to_have_url(app.url("/contact"))
    expect(app.heading).to_have_text("Contact")

    app.navigation.back()
    expect(app.page).to_have_url(app.url())
    app.navigation.forward()
    expect(app.page).to_have_url(app.url("/contact"))


def test_contact_form(app: DemoApp):
    app.open("/contact")
    app.contact.fill(name="Ana", email="ana@example.com", subject="Sales")
    app.contact.submit()

    expect(app.contact.status).to_have_text("Message sent by Ana")


def test_mock_api_response(app: DemoApp):
    app.tasks.mock_response([{"id": "mock-1", "title": "Mock task"}])
    app.open_tasks()
    expect(app.tasks.items).to_have_text(["Mock task"])
