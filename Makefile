.PHONY: test check quality run clean

test:
	python -m pytest

check:
	./check.sh

quality:
	./quality.sh

run:
	./run.sh

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
	rm -rf .coverage coverage.xml htmlcov .mypy_cache .ruff_cache
