#!/bin/bash
set -e

echo "Running isort..."
isort src tests main.py
echo "Running black..."
black src tests main.py
echo "Running flake8..."
flake8 src tests main.py
echo "Running pytest..."
pytest --cov=src tests/
