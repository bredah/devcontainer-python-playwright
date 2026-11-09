"""Launch authenticated, loopback-only Jupyter without logging its token."""

import os

from jupyter_server.serverapp import ServerApp


def main():
    token = os.environ.get("JUPYTER_TOKEN", "").strip()
    if len(token) < 32:
        raise SystemExit(
            "Set JUPYTER_TOKEN to at least 32 characters; run make env-init."
        )
    port = int(os.environ.get("PROJECT_JUPYTER_PORT", "8888"))
    app = ServerApp.instance()
    app.initialize(
        [
            "--ServerApp.root_dir=notes",
            "--ServerApp.ip=127.0.0.1",
            f"--ServerApp.port={port}",
            "--ServerApp.port_retries=0",
            "--ServerApp.open_browser=False",
            "--ServerApp.allow_remote_access=False",
            "--ServerApp.log_level=WARN",
            '--ServerApp.jpserver_extensions={"jupyterlab": True}',
        ]
    )
    # Enforce authentication even if user-level Jupyter settings disabled it.
    app.identity_provider.token = token
    print(
        f"JupyterLab: http://127.0.0.1:{port}/lab (use JUPYTER_TOKEN from the local .env)",
        flush=True,
    )
    app.start()


if __name__ == "__main__":
    main()
