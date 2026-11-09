# Interactive notebooks (devcontainer only)

The devcontainer automatically installs the optional Poetry `notebooks` group:
JupyterLab, ipykernel and nbclient. The standalone Docker test runner explicitly
installs only `main,dev`; it includes neither Jupyter nor these notebooks or the
notebook session adapter. Keep notebook work inside the devcontainer.

## Start

Rebuild and reopen the devcontainer to apply its dependency installation step.
For an existing container, run `make notes-install` once.

```bash
make env-init # Generate a private Jupyter token in the ignored .env.
make demo    # First terminal: local API and web application on port 8765.
make notes   # Second terminal: JupyterLab on localhost:8888.
```

Open `http://127.0.0.1:8888/lab` and paste the `JUPYTER_TOKEN` from your local
`.env` into the login form. The launcher does not print the token. VS Code forwards
port 8888 on localhost only.
Alternatively, open a notebook in VS Code and select the project
`.venv/bin/python` kernel. Keep token authentication enabled. Override the Jupyter
port with `make notes JUPYTER_PORT=8889` and forward it manually.

## Choose a notebook

| Notebook | Workflow |
| --- | --- |
| [api.ipynb](api.ipynb) | Reuse `TasksAPI`, inspect status/headers/JSON, create/read/delete a task, validate and export data |
| [web.ipynb](web.ipynb) | Reuse `DemoApp`, navigate, submit a form, scrape links, export CSV and display screenshots |

Run cells in order. `BASE_URL` points to the local demo by default. Adapt it and
the relevant API client/components for your own application. The API notebook
deletes only the task it created. Exports go to ignored `notes/output/`.
Keep committed notebooks free of outputs and credentials.

## Reuse synchronous Playwright scripts

Jupyter already runs an asyncio loop. `NotebookSession` keeps synchronous
Playwright objects on one worker thread so existing clients and components can
be used without rewriting them:

```python
from notebooks import NotebookSession

session = await NotebookSession.api("http://127.0.0.1:8765")
rows = await session.run(lambda api: api.list().json())
assert isinstance(rows, list)
await session.close()
```

The notebooks locate the repository and add `src` to the import path. For browser
work, use `await NotebookSession.web(BASE_URL)`; the devcontainer connects to
`PLAYWRIGHT_WS_ENDPOINT` and forwards loopback to the Python client.

Run a reusable scraping function with
`await session.run(lambda app: your_script(app.page))`. See
`src/components/scraping.py` for `extract_links`. Return dictionaries, lists,
strings or bytes from callbacks, not live Playwright objects. Async callbacks
are not supported. API-only sessions do not launch a browser.

Always run `await session.close()` before recreating a session or when finished,
including after failed exploratory cells. Stop the demo with Ctrl+C afterwards.
Notebook state is independent of pytest fixtures and CLI sessions.

## Environment configuration

Run `make env-init` at the project root and set `BASE_URL` and any
application-specific variables there. Use `make source=.env notes` or
`make ENV_FILE=.env.local notes` to choose a file. The notebooks load it through
`python-dotenv` and preserve already exported process variables. `BASE_URL` is
read before creating a session; rerun setup after configuration changes, closing
any prior session first. Keep the remote browser endpoint supplied by the
devcontainer, and do not put secrets in notebook cells or outputs.

## Troubleshooting connection failures

`ERR_SOCKS_CONNECTION_FAILED` while opening `http://127.0.0.1:8765` can mean the
remote browser's loopback tunnel cannot reach the demo server. A successful
browser connection does not start the application. Run `make demo` in a separate
terminal **inside the same devcontainer** and keep it running, then restart the
notebook kernel and run setup again. API requests need this server as well.

Notebook session setup checks TCP reachability before opening Playwright resources
and reports a direct `Cannot reach ...; run make demo` error when it is unavailable.
For a different application, verify `BASE_URL` instead of starting the demo.
If you recently changed Compose networking, rebuild and reopen the devcontainer;
already running containers retain their previous network settings.

## Kernel discovery

Select **Python (project .venv)** (`project-python`). `make notes`,
`make notes-install` and devcontainer creation register it inside the Poetry
virtual environment using an absolute interpreter path. After registration,
refresh JupyterLab or reselect the kernel in VS Code. If VS Code is running on
the host, reopen the folder in the devcontainer first; a Linux virtual environment
cannot run as a macOS host interpreter.

To register manually inside the devcontainer:

```bash
poetry run python -m ipykernel install --sys-prefix --name project-python --display-name "Python (project .venv)"
```

The kernelspec lives under `.venv/share/jupyter/kernels/project-python`; recreate
it after replacing or relocating `.venv`. If discovery still fails, run
`poetry run jupyter kernelspec list` inside the same environment as JupyterLab.
