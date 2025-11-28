#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Running Rust tests..."
(cd "$SCRIPT_DIR/raspberry_pi" && rustc --test src/console_format.rs -o /tmp/console_format_test)
/tmp/console_format_test
rm /tmp/console_format_test

echo ""
echo "Running Python tests..."
(cd "$SCRIPT_DIR/cloud" && uv run pytest tests/ -v)
