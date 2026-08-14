#!/bin/bash

set -e

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
echo ">>> Tests"
python -m pytest

echo ""
echo ">>> Git"
git status

echo ""
echo "================================"
echo " Health check complete"
echo "================================"
