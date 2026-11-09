# Python test execution and debugging

This project uses Poetry, pytest and the synchronous Python Playwright API.
Run these commands inside the devcontainer from the repository root:

```bash
poetry run pytest -v
poetry run pytest tests/api -v
poetry run pytest tests/web -v
poetry run pytest tests/e2e -v
poetry run pytest tests/web/test_navigation.py::test_contact_form -v
poetry run pytest --last-failed -v
```

Use the traceback and retained artifacts in `test-results/` to investigate failures.
For interactive browser inspection, reproduce the scenario in a separate CLI session:

```bash
# Separate terminal; stop with Ctrl+C after exploration.
poetry run python -m tests.mock.demo_app --port 8765

# Another terminal, same devcontainer and working directory.
poetry run playwright cli -s=demo open http://127.0.0.1:8765/contact
poetry run playwright cli -s=demo snapshot
poetry run playwright cli -s=demo console
poetry run playwright cli -s=demo requests
poetry run playwright cli -s=demo close
```

The CLI configuration uses the Compose Playwright service, forwarding loopback to
this Python container. CLI sessions do not inherit pytest fixtures or their data.
Recreate relevant preconditions before diagnosing. Use current snapshot refs for
interactions. Fix reusable locators/actions in `src/components`, HTTP operations
in `src/api`, and expectations in the tests. Rerun the affected tests after changes.

The JavaScript runner's `npx playwright test --debug=cli` and `tw-*` attachment
instructions do not apply to this pytest setup. Do not switch frameworks or
weaken assertions to make a failure disappear.
