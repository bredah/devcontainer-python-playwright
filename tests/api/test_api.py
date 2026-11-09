import pytest
from playwright.sync_api import expect

from api import TasksAPI


def test_list_tasks(tasks_api: TasksAPI):
    response = tasks_api.list()
    expect(response).to_be_ok()
    assert response.status == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == []


def test_create_read_and_delete_task(tasks_api: TasksAPI):
    created = tasks_api.create("Learn Playwright")
    assert created.status == 201
    task = created.json()
    assert task == {"id": "1", "title": "Learn Playwright"}

    fetched = tasks_api.get(task["id"])
    expect(fetched).to_be_ok()
    assert fetched.json() == task
    assert tasks_api.list().json() == [task]

    deleted = tasks_api.delete(task["id"])
    assert deleted.status == 204
    assert deleted.body() == b""
    assert tasks_api.get(task["id"]).status == 404


@pytest.mark.parametrize(
    "payload", [{}, {"title": ""}, {"title": "   "}, {"title": 123}]
)
def test_reject_invalid_task(tasks_api: TasksAPI, payload):
    response = tasks_api.create_payload(payload)
    assert response.status == 422
    assert response.json() == {"error": "title_required"}
    assert tasks_api.list().json() == []


def test_reject_invalid_json(tasks_api: TasksAPI):
    # Bytes send the malformed payload verbatim, without JSON serialization.
    response = tasks_api.create_raw(b"{invalid")
    assert response.status == 400
    assert response.json() == {"error": "invalid_json"}


def test_missing_task(tasks_api: TasksAPI):
    response = tasks_api.get("does-not-exist")
    assert response.status == 404
    assert response.json() == {"error": "not_found"}
