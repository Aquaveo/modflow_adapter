#!/usr/bin/env bash
mkdir -p coverage
rm -f .coverage
echo "Running Unit Tests..."
coverage run -a --rcfile=coverage.ini -m unittest -v tests.unit_tests
echo "Running Intermediate Tests..."
coverage run -a --rcfile=coverage.ini -m unittest -v tests.intermediate_tests
echo "Combined Coverage Report..."
coverage report -m
echo "Linting..."
flake8
echo "Testing Complete"