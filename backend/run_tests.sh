#!/bin/sh
# Simple script to run tests with common options

# Run all tests
run_all_tests() {
    python -m pytest
}

# Run a specific test file
run_specific_test() {
    python -m pytest $1 -v
}

# Generate HTML coverage report
generate_coverage() {
    python -m pytest --cov=core --cov=entities --cov=utils --cov-report=html
    echo "Coverage report generated in htmlcov/ directory"
}

case "$1" in
    coverage)
        generate_coverage
        ;;
    *)
        if [ -z "$1" ]; then
            run_all_tests
        else
            run_specific_test $1
        fi
        ;;
esac
