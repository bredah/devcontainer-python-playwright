# Project guidance

Python + Poetry + pytest; use `poetry run pytest` inside the devcontainer.
Tests: `tests/api` for API, `tests/web` for UI, `tests/e2e` for combined flows.
Reuse `src/api` clients and `src/components` UI components; keep assertions in tests.
In the devcontainer, browsers run in the Compose service, not locally on Wolfi.
The root Dockerfile builds a standalone runner with local browsers; its entrypoint is pytest.
Use English for code, comments, documentation and demo UI text.
Makefile targets cover Poetry tests and standalone Docker runs.
Interactive notebooks live in notes/; install their optional group with make notes-install.
Reuse synchronous clients/components in Jupyter through src/notebooks/NotebookSession
and return plain data from worker callbacks. Keep notebook outputs uncommitted.

## Retrieve context selectively

Before opening multiple source files, query the persistent symbol index:

```bash
python3 .agents/skills/code-context-graph/scripts/code_graph.py find ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py find DemoApp.__init__
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs ContactForm
python3 .agents/skills/code-context-graph/scripts/code_graph.py refs app --limit 8
```

Each query refreshes changed/deleted Python files under `src` and `tests`.
Use returned signatures, docstrings, constructor attributes and reference candidates
to reuse existing APIs without rereading entire implementations. Narrow queries
before increasing limits. Read current source around returned lines before editing
or when behavior cannot be established from metadata. Reference edges are syntactic
candidates, not fully resolved runtime dependencies or guaranteed impact analysis.
Do not dump the database, load all files, or read all skill references by default.
On index failure, report it and inspect only relevant source; never use stale results.
The ignored `.agents/skills/code-context-graph/graph.sqlite` is rebuildable and persists across chats.

## Quality checks

Use `make format` (isort then Black) and `make lint` before completing Python changes.
The optional Poetry quality group provides the tools; the devcontainer installs it.
pre-commit manages the Git hook. Flake8 checks errors and McCabe complexity <= 10.
Run the code graph's script tests after changing its extraction or persistence.

## Commit messages

Every commit must follow Conventional Commits in English. Read
`.agents/skills/conventional-commits/SKILL.md` when preparing a commit.
The commit-msg hook enforces the repository's allowed types and header structure.
Do not create commits unless requested; do not bypass message validation.

## Local service security

Bind application, demo and Playwright listeners to 127.0.0.1 only. The Compose
services share a network namespace; do not publish Docker ports or add wildcard
binds. Jupyter requires JUPYTER_TOKEN from the ignored local .env; use make env-init.
Never display, stage or commit .env, tokens or generated artifacts.
