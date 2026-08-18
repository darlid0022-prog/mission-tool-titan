#!/usr/bin/env bash

set -euo pipefail

required_modules=(ruff mypy pytest_cov pip_audit detect_secrets)
missing_modules=()

for module in "${required_modules[@]}"; do
    if ! python -c "import ${module}" >/dev/null 2>&1; then
        missing_modules+=("${module}")
    fi
done

if ((${#missing_modules[@]} > 0)); then
    echo "Development quality tools are not installed:"
    printf '  - %s\n' "${missing_modules[@]}"
    echo ""
    echo "Install the pinned toolchain with:"
    echo "  python -m pip install -r requirements-dev.txt"
    exit 2
fi

echo "================================"
echo " Mission Tool - Quality Check"
echo "================================"

echo ""
echo ">>> Format"
python -m ruff format --check .

echo ""
echo ">>> Lint"
python -m ruff check .

echo ""
echo ">>> Types"
python -m mypy app_services.py mission trajectory.py

echo ""
echo ">>> Tests and coverage"
python -m pytest \
    --cov=app_services \
    --cov=mission \
    --cov=trajectory \
    --cov-report=term-missing \
    --cov-report=xml

echo ""
echo ">>> Dependency audit"
python -m pip_audit

echo ""
echo ">>> Secret scan"
python -m detect_secrets scan \
    app.py \
    app_services.py \
    trajectory.py \
    launch_window_plot.py \
    launch_window_service.py \
    mission \
    pages \
    tests \
    scripts \
    docs \
    .streamlit \
    .gitignore \
    Makefile \
    check.sh \
    quality.sh \
    environment.yml \
    requirements-dev.txt \
    pyproject.toml

echo ""
echo "================================"
echo " Quality check complete"
echo "================================"
