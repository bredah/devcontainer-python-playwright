.DEFAULT_GOAL := help
.SILENT:
SHELL := /bin/bash
source ?= .env
ENV_FILE ?= $(source)
export PROJECT_ENV_FILE := $(abspath $(ENV_FILE))
export PROJECT_ENV_REQUIRED := $(if $(filter command line,$(origin source) $(origin ENV_FILE)),1,0)
LOAD_ENV := source "$(CURDIR)/scripts/load_env.sh";
.SHELLFLAGS := -eu -c
PYTHON ?= python3
POETRY ?= poetry
DOCKER ?= docker
IMAGE ?= python-playwright-tests:local
ARGS ?= -v
JUPYTER_PORT ?= 8888

.PHONY: help install test test-api test-web test-e2e docker-build docker-test docker-test-api docker-test-web docker-test-e2e notes-install notes demo
.PHONY: quality-install hooks-install format lint

help:
	@$(LOAD_ENV) printf "\nProject commands\n\n"; \
	printf "  %-29s %s\n" \
	  'Environment' 'make source=.env <target> (or ENV_FILE=.env.local)' \
	  'env-init' 'Create private .env and Jupyter token' \
	  'install' 'Install test dependencies' \
	  'test[-api|-web|-e2e]' 'Run tests through Poetry; override ARGS' \
	  'docker-build' 'Build the test image; override IMAGE' \
	  'docker-test[-api|-web|-e2e]' 'Run tests in the Docker image' \
	  'notes-install' 'Install notebook dependencies' \
	  'notes' 'Start authenticated Jupyter on 127.0.0.1' \
	  'demo' 'Start the loopback-only demo application' \
	  'quality-install' 'Install quality tools' \
	  'hooks-install' 'Install formatting and commit-message hooks' \
	  'format' 'Apply isort and Black' \
	  'lint' 'Check formatting, imports and complexity'; \
	printf "\nExample: make source=.env test-api ARGS=-q\n\n"

PYTHON_PATHS = src tests scripts .agents/skills

quality-install:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) install --with quality

hooks-install:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run pre-commit install --hook-type pre-commit --hook-type commit-msg

format:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run isort $(PYTHON_PATHS)
	$(LOAD_ENV) $(POETRY) run black $(PYTHON_PATHS)

lint:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run isort --check-only $(PYTHON_PATHS)
	$(LOAD_ENV) $(POETRY) run black --check $(PYTHON_PATHS)
	$(LOAD_ENV) $(POETRY) run flake8 $(PYTHON_PATHS)

install:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) install

test:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run pytest $(ARGS)

test-api:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run pytest tests/api $(ARGS)

test-web:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run pytest tests/web $(ARGS)

test-e2e:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run pytest tests/e2e $(ARGS)

docker-build:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(DOCKER) build -t $(IMAGE) .

docker-test:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) bash scripts/docker_env.sh $(DOCKER) run --rm --init --shm-size=1g $(IMAGE) $(ARGS)

docker-test-api:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) bash scripts/docker_env.sh $(DOCKER) run --rm --init --shm-size=1g $(IMAGE) tests/api $(ARGS)

docker-test-web:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) bash scripts/docker_env.sh $(DOCKER) run --rm --init --shm-size=1g $(IMAGE) tests/web $(ARGS)

docker-test-e2e:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) bash scripts/docker_env.sh $(DOCKER) run --rm --init --shm-size=1g $(IMAGE) tests/e2e $(ARGS)

notes-install:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) install --with notebooks

notes:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) PROJECT_JUPYTER_PORT="$(JUPYTER_PORT)" $(POETRY) run python scripts/start_notes.py

demo:
	@printf "\n[%s]\n\n" "$@"
	$(LOAD_ENV) $(POETRY) run python -m tests.mock.demo_app --port 8765

.PHONY: env-init
env-init:
	@PROJECT_ENV_FILE="$(PROJECT_ENV_FILE)" $(PYTHON) scripts/init_env.py
