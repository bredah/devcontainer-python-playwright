# Python testing workspace

API, browser and end-to-end testing with Python, Poetry, pytest and Playwright.
The project includes reusable clients/components, a Chainguard devcontainer,
a standalone Docker test image, interactive notebooks and local agent skills.
Example tests use a local demo application, without requiring public websites.

## Requirements

- Docker for the devcontainer, standalone tests and dependency security reports.
- VS Code with Dev Containers for interactive development.
- Python 3.11+ and Poetry 2.5.1 only if running outside the devcontainer.
- Make and Bash for the provided shortcuts. Run `make help` to list them.

The devcontainer runs Python on Chainguard/Wolfi and browsers in the official
Playwright Ubuntu service. Both share a network namespace, allowing the browser
server to listen only on `127.0.0.1`. The standalone test image runs Python and
browsers together, without requiring the devcontainer.

## Start developing

1. Start Docker and open this folder in VS Code.
2. Run **Dev Containers: Reopen in Container**.
3. Wait for dependency installation and kernel registration to finish.
4. Inside the devcontainer, run:

```bash
make env-init
make test-api
make test-web
make test-e2e
```

The devcontainer installs the test, notebook and quality groups. Poetry itself is
isolated in `/opt/poetry`; project dependencies use `.venv`. It runs as `nonroot`.
Rebuild/reopen after changes to Dockerfiles, Compose or devcontainer configuration.
Do not share the same `.venv` between host and container runtimes.

For local Python on a supported Playwright OS:

```bash
poetry install --with quality
poetry run playwright install chromium
make test
```

On supported Linux, `poetry run playwright install --with-deps chromium` also
installs system dependencies and needs elevated privileges. Do not install local
browsers in Wolfi; its devcontainer uses the remote browser service.

## Project structure

```text
src/
  api/                  # Reusable HTTP clients (TasksAPI)
  components/           # DemoApp, navigation, forms, task list, scraping
  notebooks/            # Jupyter adapter for synchronous Playwright code
  environment.py        # Local configuration loading
tests/
  api/                  # API contracts, status codes and negative scenarios
  web/                  # Browser-only navigation, forms and mocking
  e2e/                  # Combined API and browser workflows
  mock/demo_app.py      # Local demo API and HTML application
  conftest.py           # Shared fixtures and resource cleanup
notes/                  # API/web notebooks and usage guide
scripts/                # Environment, quality/reporting and notebook helpers
.agents/skills/         # Browser automation, code context and commit guidance
```

Keep HTTP endpoints in `src/api`, locators/actions in `src/components`, and
assertions in tests. Reuse fixtures such as `tasks_api`, `app`, `api`, `page` and
`demo_url`. Each example test gets its own local server and state. API-only tests
do not launch browsers. This is a dependency-only Poetry project, not an installed
Python package; pytest and VS Code add `src` to their import paths.

## Run tests

```bash
make test
make test-api
make test-web
make test-e2e
make test-web ARGS='-v --browser firefox'
make test-e2e ARGS='-v --browser webkit'
poetry run pytest tests/web/test_navigation.py::test_contact_form -v
```

Browser screenshots/traces are retained on failures under `test-results/`.
To generate a standalone HTML report locally:

```bash
make test-api ARGS='-v --html=reports/api.html --self-contained-html'
```

API, web and e2e can also be selected independently in the repository's manual
workflow. Their results are grouped into a final dashboard and downloadable
report bundle. Generated reports are ignored by Git.

## Run the standalone Docker image

From a host with Docker access:

```bash
make docker-build
make docker-test
make docker-test-api
make docker-test-web ARGS='-v --browser firefox'
make docker-test-e2e
```

Override the image with `IMAGE=my-tests:tag`. Rebuild after dependency, source or
test changes. The image runs as `pwuser` and installs only Poetry groups `main,dev`;
it excludes Jupyter, quality tools, notebooks and their adapter. pytest exit codes
are preserved. No service ports are published.

The Make targets remove containers after execution. To preserve HTML or failure
artifacts, retain a named container and copy its files before removing it:

```bash
docker run --name test-run --init --shm-size=1g python-playwright-tests:local \
  tests/web --html=reports/web.html --self-contained-html
docker cp test-run:/app/reports ./docker-test-results
docker cp test-run:/app/test-results ./docker-browser-results
docker rm test-run
```

## Environment and local access

```bash
make env-init
make source=.env test-api
make ENV_FILE=.env.local notes
```

`make env-init` creates a private `.env` with a random 256-bit `JUPYTER_TOKEN`,
without displaying it, and preserves an existing token. `.env` has mode 0600 and
is excluded from Git and Docker builds; `.env.example` contains no secrets.

Make loads the default `.env` if present. `source=.env` selects it explicitly;
`-source` is not valid Make syntax. Bash sourcing exports values and supports
quoted strings and variable expansion, so only source files you control. An
explicitly selected missing file fails. Use Make command-line settings for
`IMAGE`, `ARGS`, `JUPYTER_PORT`, `POETRY` and `DOCKER`.

Python uses `python-dotenv` without replacing existing process variables. For
direct Python execution, `DOTENV_PATH` selects another file. Notebooks read
`BASE_URL`; tests retain their isolated demo URLs. Docker test targets forward
application variables from the selected file, but exclude Jupyter credentials.
Do not set the devcontainer-only browser endpoint for standalone Docker tests.

Jupyter, the demo and Playwright bind only to `127.0.0.1`. VS Code forwards Jupyter
on localhost; other ports are not automatically forwarded. Keep forwarding private
and avoid wildcard bindings. Local processes in the shared namespace can still
reach these services. No Docker socket is mounted in the devcontainer.

## Notebooks (devcontainer only)

```bash
make env-init
make notes-install  # Needed only when updating an existing container.
make demo           # Keep running in a separate devcontainer terminal.
make notes          # Start JupyterLab on http://127.0.0.1:8888/lab.
```

Paste the token from `.env` into Jupyter's login form. It is not printed in the
startup logs or passed on the command line. Select **Python (project .venv)**
(`project-python`); `make notes`, `make notes-install` and devcontainer creation
register it with the absolute `.venv` interpreter path.

- `notes/api.ipynb`: inspect API responses, validate data and export JSON.
- `notes/web.ipynb`: navigate, use components, scrape links, export CSV and display screenshots.

Open notebooks directly in VS Code if preferred; `make notes` is needed only for
browser-based JupyterLab. Keep `make demo` running for either interface. Run cells
in order and close sessions after exploration. Outputs go to ignored `notes/output/`.
See [notes/README.md](notes/README.md) for reuse patterns and troubleshooting.

## VS Code and code quality

Python, Jupyter, Black Formatter and isort must be installed **in the devcontainer**.
If an extension is disabled because it requires the Remote Extension Host, select
**Install in Dev Container: Python · Chainguard**, then **Developer: Reload Window**.
The project declares these extensions in the devcontainer and `.vscode` settings.

Python files use Black on save and isort on explicit saves, using the selected
`.venv` and `pyproject.toml`. Notebook kernel selection is independent of formatting.

```bash
make quality-install  # For an existing environment.
make hooks-install
make format
make lint
```

[pre-commit](https://pre-commit.com/) manages the formatting and `commit-msg` hooks.
isort uses its Black-compatible profile; Black uses 88 columns; Flake8 checks errors
and McCabe complexity <= 10. Install hooks in each clone and in the environment
where you make commits. Inspect and restage formatter changes before retrying a
commit. Notebook cells are outside the Python-file hooks; clear their outputs.

All commits use English Conventional Commits, for example:
`feat(api): add task search`, `fix(notes): validate target connection`, or
`chore(quality): configure hooks`. The allowed types are documented in the local
`conventional-commits` skill and enforced by `commit-msg`.

## Locked versions and DevSecOps delivery

Every direct dependency in `pyproject.toml` has an exact `==` version. `poetry.lock`
fixes transitive versions and distribution hashes. Commit both together. Updating
a package is intentional: use `poetry add --group dev package==X.Y.Z` (or the relevant
group), regenerate the lockfile and rerun validation. Avoid broad `poetry update`
when you do not intend to change the dependency set.

Playwright is `1.65.0`; keep its dependency version aligned with both Docker image
tags and the Compose server command. Poetry itself is pinned to `2.5.1`. The
Chainguard `latest-dev` base can still change Python/system packages; pin a validated
image digest if the development runtime must also be immutable.

Run on the host with Python 3.11+ and Docker access:

```bash
make security
# Aliases: make sbom or make sarif
```

The pinned Trivy image produces these files in `reports/security/`:

| File | Purpose |
| --- | --- |
| `sbom.cdx.json` | CycloneDX inventory of all packages/versions in the Poetry lockfile |
| `dependencies.sarif` | SARIF 2.1.0 vulnerability findings for those dependencies |
| `scan-metadata.json` | Scanner identity, lockfile SHA-256, package count and finding count |

Deliver all three to DevSecOps. **SARIF is a findings format, not a complete package
inventory**; a package with no known vulnerability may not appear as a SARIF result.
The SBOM is checked against every locked package/version, including optional
notebook and quality groups. This is a repository dependency inventory, not an
SBOM of installed container OS/browser packages.

The scanner receives only copied dependency manifests, a cache and its output
directory, not `.env` or source code. It runs without a Docker socket mount or
privileged capabilities. Internet is needed to pull the pinned scanner and update
its advisory database; no project upload service is used. Scanner errors fail the
command. Findings are reported without blocking by severity; DevSecOps sets the
remediation policy. Failed generation must not be interpreted as a clean scan.

The same `make security` runs after result consolidation, even when tests fail.
Download `devsecops-dependency-reports` from the workflow artifacts (30-day retention).
No GitHub Code Scanning entitlement is required to download the SARIF. See
[docs/security.md](docs/security.md) for scope and reproducibility details.

## Agent skills and selective code retrieval

- `playwright-cli`: explore the browser and author Python tests with existing components.
- `code-context-graph`: local code/document search plus Python symbol/reference queries.
- `conventional-commits`: prepare and validate commit messages.

Inside the devcontainer, explore the running demo with:

```bash
poetry run playwright cli -s=demo open http://127.0.0.1:8765/contact
poetry run playwright cli -s=demo snapshot
poetry run playwright cli -s=demo close
```

For local context retrieval without uploading files:

```bash
python3 .agents/skills/code-context-graph/scripts/code_graph.py search "Jupyter authentication token" --limit 5
python3 .agents/skills/code-context-graph/scripts/code_graph.py find ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs app.contact
```

The ignored SQLite cache lives beside the skill, updates incrementally and returns
bounded excerpts. Search is lexical, not embedding-based. Read the skill for its
explicit file allowlist and limitations. Automatic discovery depends on the agent;
`AGENTS.md` requires agents to use `code-context-graph` before searching code or
opening implementations for discovery. Direct reads of relevant results remain
necessary before editing. A bounded direct-search fallback is allowed only for
index errors, no useful matches after narrowing, or content outside the allowlist;
the agent must explain why. This is a repository instruction for compliant agents,
not a sandbox that can intercept arbitrary external tools. No `.env`, outputs or
database caches should be committed.
