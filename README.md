# Python, Playwright and pytest

A reusable API and browser testing project with Poetry, a Chainguard Python
devcontainer, an independent Docker test runner, and local agent skills.
All example tests use a local demo application; they do not depend on public sites.

## Choose how to run

| Workflow | Requirements | Browser execution |
| --- | --- | --- |
| Docker test image | Docker | Inside the test container |
| VS Code devcontainer | Docker, VS Code, Dev Containers extension | Remote Playwright service in Compose |
| Local Python | Python 3.11+, Poetry 2, supported Playwright OS | Local browser installation |

The devcontainer uses Chainguard/Wolfi. Since Wolfi is not an officially supported
Playwright browser distribution, browsers run in a separate Ubuntu-based service.
The standalone test image uses the official Playwright Ubuntu image with Python
installed, so it can run the whole suite without the devcontainer or Compose.

## Run tests with Docker

Run from the repository root. The first build requires internet access to download
system packages and locked Python dependencies; tests themselves run locally.

```bash
# Build the runner, including the browsers, source code and tests.
docker build -t python-playwright-tests:local .

# Run the entire suite. pytest's exit code becomes the container exit code.
docker run --rm --init --shm-size=1g python-playwright-tests:local

# Select a test directory or browser; arguments are passed directly to pytest.
docker run --rm --init --shm-size=1g python-playwright-tests:local tests/api -v
docker run --rm --init --shm-size=1g python-playwright-tests:local tests/web --browser firefox -v
docker run --rm --init --shm-size=1g python-playwright-tests:local tests/e2e --browser webkit -v
```

The image runs as `pwuser`, installs Poetry in `/opt/poetry` and dependencies in
`/opt/test-venv`, and includes only the project files needed to run tests.
It does not include local virtual environments, SQLite caches, skill instructions
or generated artifacts. Rebuild after changing source, tests or dependencies.
The runner uses local browsers; do not pass `PLAYWRIGHT_WS_ENDPOINT` unless you
intentionally want a remote browser instead.

To retain artifacts even when a test fails, use a named container and copy results
before removing it:

```bash
docker run --name playwright-test-run --init --shm-size=1g python-playwright-tests:local
docker cp playwright-test-run:/app/test-results ./docker-test-results
docker rm playwright-test-run
```

In CI, preserve the exit status from `docker run`; collect artifacts in an always-run
cleanup step. Do not let artifact collection mask a failed test run. When using a
bind mount for artifacts, ensure its directory is writable by the container user.

## Develop in VS Code

1. Start Docker Desktop or a compatible Docker daemon.
2. Install the VS Code **Dev Containers** extension (`ms-vscode-remote.remote-containers`).
3. Open this directory and run **Dev Containers: Reopen in Container**.
4. Wait for `poetry install --with notebooks,quality` to finish, then run `poetry run pytest -v`.

The `python` service uses `cgr.dev/chainguard/python:latest-dev`, with Git, Bash,
GNU tar, and POSIX libc utilities required by VS Code Server. It runs as `nonroot`.
Poetry is isolated in `/opt/poetry`; project dependencies live in `.venv`.
VS Code selects `.venv/bin/python` and discovers tests under `tests/`.

The `playwright` service supplies Chromium, Firefox and WebKit through
`ws://127.0.0.1:3000/`. The services share a network namespace, allowing the
browser server to bind only to loopback. It has a health check and publishes no
Docker ports to the host.
Its first startup requires npm access. The `connect_options` fixture forwards
loopback traffic so remote browsers can reach per-test servers in the Python container.
After changing `.devcontainer/Dockerfile` or Compose configuration, use
**Dev Containers: Rebuild and Reopen in Container**.

`latest-dev` is a moving tag and can change Python versions. Pin a validated image
digest if you need a reproducible development runtime. If `.venv` was created on
another OS or Python runtime, recreate that disposable environment in the intended
runtime with `poetry env remove --all` followed by `poetry install`.

## Run with local Python

Use Python 3.11+ and Poetry 2 on a supported Playwright system:

```bash
poetry install
poetry run playwright install chromium
poetry run pytest -v
```

On supported Linux distributions, browser system dependencies may also be needed:
`poetry run playwright install --with-deps chromium` (requires elevated privileges).
Install Firefox or WebKit explicitly if you want to select those browsers locally.
Do not use this browser-installation workflow inside the Wolfi devcontainer.

## Test commands and examples

```bash
poetry run pytest -v
poetry run pytest tests/api -v
poetry run pytest tests/web -v
poetry run pytest tests/e2e -v
poetry run pytest tests/web/test_navigation.py::test_contact_form -v
poetry run pytest --browser firefox -v
poetry run pytest --browser webkit -v
```

| Directory/file | Examples |
| --- | --- |
| `tests/api/test_api.py` | GET, POST, DELETE, JSON, headers, lifecycle, invalid inputs, and HTTP 200/201/204/400/404/422 |
| `tests/web/test_browser.py` | Minimal HTML, accessible locators and clicking |
| `tests/web/test_navigation.py` | Links, history, contact form, selectors and request mocking |
| `tests/e2e/test_api_and_browser.py` | Create data through the API and verify it in the UI |

The `demo_url` fixture starts an isolated HTTP server on a free port for each test.
It cleans up the server afterwards. API-only tests use Playwright's
`APIRequestContext` without launching a browser. Browser traces and screenshots
are retained on failure under `test-results/`. These artifacts are ignored by Git.
The demo server is test support code, not a production application.

## Reuse clients, components and fixtures

```text
src/
  api/tasks.py              # TasksAPI: task HTTP endpoints
  components/
    app.py                  # DemoApp: URLs, page opening and composition
    navigation.py           # Navigation links and browser history
    contact.py              # Form locators and actions
    tasks.py                # Task list and response mocking
tests/
  api/                      # HTTP contracts and validation
  web/                      # Browser-only behavior
  e2e/                      # Combined API/browser scenarios
  mock/demo_app.py          # Local HTML and API server
  conftest.py               # Shared fixtures and resource cleanup
.agents/skills/
  playwright-cli/           # Browser exploration and Python test authoring
  code-context-graph/       # Persistent symbol index, tools and SQLite cache
```

Keep endpoints in API clients and locators/actions in UI components. Keep expected
outcomes and assertions in tests. `TasksAPI` returns raw `APIResponse` objects so
positive and negative cases can share the same client. Example:

```python
from playwright.sync_api import expect
from api import TasksAPI
from components import DemoApp


def test_new_task(tasks_api: TasksAPI, app: DemoApp):
    response = tasks_api.create("Review the tests")
    assert response.status == 201

    response = app.open_tasks()
    assert response.ok
    expect(app.tasks.items).to_have_text(["Review the tests"])
```

Fixtures include `app`, `tasks_api`, `api`, `demo_url` and the pytest-playwright
`page` fixture. pytest adds `src` to its import path; VS Code uses
`python.analysis.extraPaths`. The project uses Poetry's dependency-only mode
(`package-mode = false`); it does not install itself as a Python package.

## Manage dependencies and versions

```bash
poetry add --group dev <package>
poetry install
poetry check --lock
```

Commit `pyproject.toml` and `poetry.lock` together. `poetry.toml` keeps local Poetry
virtual environments inside the project. Use `poetry update` only when you intend
to update locked dependency versions.

Playwright is pinned to `1.65.0`. When upgrading it, align the dependency and lock
with both Docker image tags (`Dockerfile` and `.devcontainer/compose.yaml`) and
the Compose `npx playwright@...` command. Rebuild images afterwards. The Python
package, browser images and remote server must use matching Playwright versions.

## Use the Playwright CLI skill

Agents that support local skills can load `.agents/skills/playwright-cli/SKILL.md`.
For example, ask: "Use $playwright-cli to explore the contact form and add Python
pytest cases under tests/web, reusing src/components."

Inside the devcontainer, from the repository root, start the demo in one terminal:

```bash
poetry run python -m tests.mock.demo_app --port 8765
```

In another terminal:

```bash
poetry run playwright cli -s=demo open http://127.0.0.1:8765/contact
poetry run playwright cli -s=demo snapshot
# Use element refs from the current snapshot for fill, click, check, etc.
poetry run playwright cli -s=demo close
```

Stop the demo server with Ctrl+C. The versioned `.playwright/cli.config.json`
connects the CLI to remote Chromium and exposes loopback traffic to the Python
client. This configuration is for the devcontainer network; it is independent of
pytest fixtures and is not copied into the standalone test image. CLI exploration
does not inherit per-test fixture state. Generated snapshots live in `.playwright-cli/`.
The skill uses Python/pytest rather than the Node Playwright test runner.

## Use the persistent code-context graph

The independent `.agents/skills/code-context-graph` skill uses Python AST and SQLite
without additional dependencies. Any agent with file and Python access can use it;
automatic skill discovery depends on the agent. Ask: "Use $code-context-graph to
locate reusable components before adding tests."

```bash
python3 .agents/skills/code-context-graph/scripts/code_graph.py find ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py find DemoApp.__init__
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs app.contact
python3 .agents/skills/code-context-graph/scripts/code_graph.py refresh
python3 .agents/skills/code-context-graph/scripts/test_code_graph.py
```

Use `--root /absolute/project/path` when running outside the target project.
The index is stored beside the skill at
`.agents/skills/code-context-graph/graph.sqlite`, ignored by Git. Each query checks
SHA-256 hashes, reparses changed files and removes deleted entries. Repeated queries
reuse unchanged metadata. The database can be deleted and rebuilt.

Results include signatures, source docstrings, constructor handles, locations and
candidate references. The script reads file bytes to check hashes, but does not
send full source bodies into the agent's context. Agents should inspect current
source before editing behavior or whenever metadata is insufficient.

Only Python under `src` and `tests` is indexed. Static references do not fully resolve
dynamic dispatch, aliases or fixture overrides. Syntax errors abort queries rather
than returning stale results. Configuration files and external libraries need
separate inspection. `AGENTS.md` documents this retrieval workflow.

## References

- [Chainguard Python image](https://images.chainguard.dev/directory/image/python/overview)
- [Poetry basic usage](https://python-poetry.org/docs/basic-usage/)
- [Playwright installation](https://playwright.dev/python/docs/intro)
- [Playwright Docker and remote browsers](https://playwright.dev/python/docs/docker)
- [Playwright API testing](https://playwright.dev/python/docs/api-testing)

## Makefile shortcuts

GNU Make is included in the devcontainer (rebuild it to install Make and the Jupyter
extension). On the host, install Make or use the underlying commands shown by
`make -n <target>`. Local targets run in the current Python environment; Docker
targets require access to a Docker daemon, typically from the host.

```bash
make help
make install
make test-api
make test-web ARGS='-v --browser firefox'
make test-e2e
make test
make docker-build
make docker-test-api
make docker-test-web ARGS='-v --browser webkit'
make docker-test-e2e
make docker-test
```

Build the image before Docker test targets and rebuild after code/dependency changes.
Override `IMAGE=my-tests:tag`, `POETRY=/path/to/poetry`, or `DOCKER=...` as needed.
Docker target exit codes reflect pytest results. Make uses the already installed
Poetry environment and does not install dependencies on every test invocation.

## Interactive notebooks in notes/ (devcontainer only)

The devcontainer automatically installs the optional Poetry `notebooks` group.
The standalone test image explicitly installs only `main,dev` and excludes
notebooks and their session adapter. Jupyter is not part of the test runner.

Inside the devcontainer:

```bash
make env-init       # Create a private local Jupyter token without displaying it.
make notes-install  # Only needed to update an already running devcontainer.
make demo           # Keep running in a separate terminal.
make notes          # Start JupyterLab on localhost:8888.
```

Open `notes/api.ipynb` or `notes/web.ipynb` in JupyterLab or VS Code using the project
`.venv` kernel. See [notes/README.md](notes/README.md) for setup, data validation,
exports, browser scraping, reuse of Playwright scripts and resource cleanup.

## Code quality and Git hooks

The Git hook framework is [pre-commit](https://pre-commit.com/). Hooks run in this
order using the versions locked by Poetry:

1. **isort** sorts Python imports with its `black` compatibility profile.
2. **Black** formats Python with an 88-character line length and Python 3.11 syntax target.
3. **Flake8/McCabe** checks Python errors and rejects functions with cyclomatic
   complexity above **10** (`C901`). Complexity measures independent control-flow
   paths; reduce branching or extract cohesive helpers when a function exceeds it.

The optional `quality` dependency group is installed automatically by the
devcontainer. It is excluded from the Docker test image, which installs only
`main,dev`. For an existing development environment:

```bash
make quality-install
make hooks-install
make format
make lint
poetry run pre-commit run --all-files
```

Hook installation is per checkout/environment. Install it where you perform Git
commits: the current hook uses the devcontainer's Python environment. If committing
from the host instead, install the quality group and reinstall the hook using that
host environment. No existing hooks are overwritten with `--overwrite`.

During a commit, pre-commit checks staged Python files. If isort or Black changes a
file, inspect the changes, stage them again and retry the commit. `--all-files`
checks Git-tracked files; `make lint` also checks untracked Python source in `src`,
`tests` and the code-graph skill scripts. The setup does not stage files for you.
Notebook cells are outside these Python-file hooks; keep notebook outputs cleared.

Configuration lives in `.pre-commit-config.yaml`, `pyproject.toml` (Black/isort)
and `.flake8` (error selection and complexity). Flake8 selects `C90,F,E9`; style
formatting is handled by Black rather than a competing line-length rule.

Generated caches, notebook exports, test artifacts, packaging files, local `.env`
files and OS/editor temporary files are ignored. The root `output/` directory is ignored and is not required by this project.

## Conventional Commits

All commit messages must follow the local
[conventional-commits skill](.agents/skills/conventional-commits/SKILL.md):

```text
feat(notes): add API exploration examples
fix(api): reject missing task titles
chore(quality): configure formatting hooks
```

Use an English header: `<type>[(scope)][!]: <description>`. Allowed lowercase types
are `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`
and `revert`. Separate an optional body with a blank line. Mark breaking changes
with `!` or a `BREAKING CHANGE:` footer.

`make hooks-install` installs both `pre-commit` (formatting/quality) and `commit-msg`
(message validation) for this checkout. The latter rejects nonconforming messages,
including default merge, revert or fixup headers; rewrite those headers to the
project format. The skill guides agents and the hook validates local commits.
Reinstall hooks in new clones and in the environment where commits are performed.
Git hooks are local; enforcing the same rule on a remote repository also requires
its CI or repository policy. No commit is created by installing the skill.

Validate a message file manually:

```bash
python3 .agents/skills/conventional-commits/scripts/check_message.py /path/to/message
poetry run pre-commit run conventional-commits --hook-stage commit-msg --commit-msg-filename /path/to/message
```

## Environment files (.env)

Initialize the local environment and edit application values as needed:

```bash
make env-init
make source=.env test-api
make source=.env test-web
make source=.env docker-test-api
make ENV_FILE=.env.local notes
```

The supported Make syntax is `source=.env` (a variable assignment), not `-source`.
Each recipe uses Bash `source` with automatic export, so commands inherit the
selected values. Only source a file you control, because shell commands inside it
are executed. A default `.env` is loaded if present; an explicitly selected missing
file fails immediately. Keep shell-compatible `KEY=value` assignments, without
spaces around `=`. Quoted values and `${OTHER_VARIABLE}` expansion are supported.
Shell sourcing replaces existing values for the keys assigned by the file.
Use Make command-line variables for Make settings such as `IMAGE`, `ARGS` and
`JUPYTER_PORT`; `.env` configures application environment variables.

Docker test targets forward application variable names assigned in the selected
file (excluding `JUPYTER_TOKEN` and `JUPYTER_TOKEN_FILE`), taking their exported, shell-expanded values. The file itself is not copied
into the image, and values are not printed in the Docker command. Do not set the
devcontainer-only `PLAYWRIGHT_WS_ENDPOINT` for standalone browser test runs.

Python uses `python-dotenv` through `environment.load_environment()` in pytest and
notebook sessions. Direct Python execution loads the project-root `.env`; set
`DOTENV_PATH=/absolute/path/to/file` to select another file. Existing process
variables take precedence in Python (`override=False`); Make already exports its
selected file's values. Notebooks read `BASE_URL` after loading the environment.
The deterministic example tests still use their isolated local demo servers.

`.env` and `.env.*` are ignored; `.env.example` is versioned. The Docker build
context excludes local environment files. The `python-dotenv` dependency is part
of the main group so both the devcontainer and standalone tests support it.

## Local network and Jupyter authentication

`make env-init` creates `.env` with a random 256-bit `JUPYTER_TOKEN`, preserves an
existing nonempty token and applies owner-only file permissions (0600). The file is
ignored by Git and excluded from Docker builds. The example contains no token.

```bash
make env-init
make notes
# Or: make source=.env notes JUPYTER_PORT=8889
```

Open `http://127.0.0.1:8888/lab` and paste `JUPYTER_TOKEN` from your local `.env`
into the login form. Make does not echo commands, and the launcher suppresses the
startup token URL. The token is passed through the environment, never a command-line
argument. Missing or short tokens are rejected; authentication is not disabled.
The launcher binds only to `127.0.0.1` and fails if the requested port is occupied.

The demo and per-test HTTP servers also bind only to `127.0.0.1`. The Playwright
server binds to `127.0.0.1:3000`; the Python container shares its network namespace
through `network_mode: service:playwright`. No Compose `ports` mappings, host
networking, wildcard listeners or Docker socket mounts are configured. VS Code
forwards only Jupyter automatically, with a localhost bind; other ports are ignored.
Do not change the forwarding visibility to public or add wildcard host mappings.

Rebuild/reopen the devcontainer after this network change. Existing containers
retain their old network configuration until recreated. Internet access remains
available for installing packages and accessing intended target websites. Loopback
binding prevents LAN exposure, but local processes and code running in the shared
container namespace can still reach these services.
