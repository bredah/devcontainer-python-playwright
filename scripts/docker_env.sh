#!/usr/bin/env bash
set -eu

# Pass exported values by name: Docker receives shell-expanded values, not quotes
# or unexpanded variables from its more restrictive --env-file parser.
docker_command="$1"
shift
if [[ "$1" != "run" ]]; then
    echo "Usage: docker_env.sh DOCKER run [arguments...]" >&2
    exit 2
fi
shift
env_flags=()
if [[ -f "${PROJECT_ENV_FILE:-}" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        if [[ "$line" =~ ^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)= ]]; then
            name="${BASH_REMATCH[2]}"
            case "$name" in
                JUPYTER_TOKEN|JUPYTER_TOKEN_FILE) continue ;;
            esac
            env_flags+=(--env "$name")
        fi
    done < "$PROJECT_ENV_FILE"
fi
exec "$docker_command" run ${env_flags[@]+"${env_flags[@]}"} "$@"
