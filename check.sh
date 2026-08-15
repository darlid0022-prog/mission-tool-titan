#!/usr/bin/env bash

set -euo pipefail

echo "================================"
echo " Mission Tool - Health Check"
echo "================================"

echo ""
echo ">>> Python"
python --version

echo ""
echo ">>> PyKEP"
python -c "import pykep; print('PyKEP OK')"

echo ""
echo ">>> Dependencies"
python -m pip check

echo ""
echo ">>> Compile"
python -m compileall -q app.py trajectory.py mission tests

echo ""
echo ">>> Tests"
python -m pytest -q

echo ""
echo ">>> Git"
git status

echo ""
echo "================================"
echo " Health check complete"
echo "================================"
