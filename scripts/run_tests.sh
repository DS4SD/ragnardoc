#!/usr/bin/env bash

set -e
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BASE_DIR"

pytest_opts=("$@")
allow_warnings=${ALLOW_WARNINGS:-"0"}
if [ "$allow_warnings" = "1" ]; then
    warn_arg=""
else
    warn_arg="-W error"
fi

# Show the test coverage when running the whole test, otherwise omit.
if [[ "${pytest_opts[*]}" != *"tests/"* ]]; then
    pytest_opts+=(
        --cov-config=.coveragerc
        --cov=ragnardoc
        --cov-report=term
        --cov-report=html
        --cov-fail-under=56
    )
fi

PYTHONPATH="${BASE_DIR}:$PYTHONPATH" python3 -m pytest \
    $warn_arg "${pytest_opts[@]}"
