# Match the Playwright package version in pyproject.toml and poetry.lock.
FROM mcr.microsoft.com/playwright:v1.65.0-noble

USER root
WORKDIR /app

# Isolate Poetry from the environment used by the test suite.
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/poetry \
    && /opt/poetry/bin/pip install --no-cache-dir poetry==2.5.1 \
    && python3 -m venv /opt/test-venv

ENV VIRTUAL_ENV=/opt/test-venv \
    PATH="/opt/test-venv/bin:/opt/poetry/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_NO_INTERACTION=1

COPY pyproject.toml poetry.lock README.md ./
# The notebook group is reserved for the development environment.
RUN poetry install --only main,dev --no-root --no-ansi

COPY --chown=pwuser:pwuser src ./src
COPY --chown=pwuser:pwuser tests ./tests
RUN mkdir -p /app/test-results /app/.pytest_cache \
    && chown -R pwuser:pwuser /app

USER pwuser
ENTRYPOINT ["/opt/test-venv/bin/python", "-m", "pytest"]
CMD ["-v"]
