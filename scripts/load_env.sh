# Sourced explicitly by each Make recipe, including older GNU Make versions.
set -eu
if [[ -f "$PROJECT_ENV_FILE" ]]; then
    set -a
    source "$PROJECT_ENV_FILE"
    set +a
elif [[ "${PROJECT_ENV_REQUIRED:-0}" == "1" ]]; then
    echo "Environment file not found: $PROJECT_ENV_FILE" >&2
    exit 1
fi

# Python entrypoints should use the same selected file instead of another .env.
export DOTENV_PATH="$PROJECT_ENV_FILE"
