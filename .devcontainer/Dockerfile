FROM cgr.dev/chainguard/python:latest-dev

USER root

# Tools needed by Git and the VS Code remote server on Wolfi.
RUN apk add --no-cache git openssh-client bash gnutar gzip libstdc++ posix-libc-utils make

# Keep Poetry isolated from the project's virtual environment.
RUN python -m venv /opt/poetry \
    && /opt/poetry/bin/python -m pip install --no-cache-dir 'poetry==2.5.1'

ENV PATH="/opt/poetry/bin:${PATH}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER nonroot

# The Python image normally forwards commands to its Python entrypoint.
ENTRYPOINT []
CMD ["sleep", "infinity"]
