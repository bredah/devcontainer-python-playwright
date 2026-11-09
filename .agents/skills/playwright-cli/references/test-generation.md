# Generate Python tests from CLI exploration

1. Read the affected tests, `tests/conftest.py`, `src/api` and `src/components`.
2. Start the target application and reproduce any required setup. For the demo,
   use `poetry run python -m tests.mock.demo_app --port 8765` in another terminal.
3. Inside the devcontainer, open a named remote session:
   `poetry run playwright cli -s=demo open http://127.0.0.1:8765`.
4. Inspect snapshots, interact with observed refs, and verify expected behavior.
   Generated snippets are evidence for locators/actions. This Python CLI emits Python; translate any JavaScript from other versions before reusing it.
5. Add or extend reusable Python components/clients for repeated operations.
   Keep test expectations explicit and use existing fixtures.
6. Place `test_*.py` files in `tests/api`, `tests/web` or `tests/e2e` as appropriate.
   Use `pytest.mark.parametrize` for input variations; no fixed sleeps.
7. Run the affected tests with `poetry run pytest <path> -v`, then required checks.
   Close your CLI session and stop the application process you started.

Example of a final combined test:

```python
from playwright.sync_api import expect
from api import TasksAPI
from components import DemoApp


def test_task_visible(tasks_api: TasksAPI, app: DemoApp):
    created = tasks_api.create("Review registration")
    assert created.status == 201

    response = app.open_tasks()
    assert response.ok
    expect(app.tasks.items).to_have_text(["Review registration"])
```

For a browser-only test, use `app.contact.fill(...)`, `app.contact.submit()` and
assert on `app.contact.status`. For API-only tests, use `tasks_api` or the `api`
APIRequestContext fixture without requesting `page` or `app`.

When debugging, reproduce the failure before changing expectations. Distinguish
an implementation defect from stale expectations using intended behavior and
available evidence; ask for clarification only when that intent is unresolved.
