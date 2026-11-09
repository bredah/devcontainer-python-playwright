from playwright.sync_api import expect

from api import TasksAPI
from components import DemoApp


def test_prepare_data_via_api_and_check_browser(tasks_api: TasksAPI, app: DemoApp):
    response = tasks_api.create("Review the tests")
    assert response.status == 201

    fetched = app.open_tasks()
    assert fetched.ok
    expect(app.tasks.items).to_have_text(["Review the tests"])
