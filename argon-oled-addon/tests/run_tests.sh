#!/bin/bash
# Run all unit tests

echo "Running unit tests for Argon OLED addon..."
echo ""

# Change to parent directory to run tests
cd "$(dirname "$0")/.."

# Run all tests in the tests directory
echo "Running all tests..."
python3 -m unittest discover -s tests -v

if [ $? -eq 0 ]; then
    echo ""
    echo "================================"
    echo "✓ All tests passed!"
    exit 0
else
    echo ""
    echo "================================"
    echo "✗ Some tests failed"
    exit 1
fi
