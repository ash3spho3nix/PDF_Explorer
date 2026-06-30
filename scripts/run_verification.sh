#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Static checks
if command -v ruff >/dev/null 2>&1; then
  ruff check .
else
  echo "ruff not installed; please install ruff to run static checks"
  exit 1
fi

if command -v mypy >/dev/null 2>&1; then
  mypy .
else
  echo "mypy not installed; please install mypy to run type checks"
  exit 1
fi

# Tests
pytest tests/unit tests/integration --cov=.

# Run sample scan and diff report
SAMPLE_DIR="tests/integration/fixtures/sample_pdfs"
OUTPUT_REPORT="tests/integration/fixtures/generated_report.md"
EXPECTED_REPORT="tests/integration/fixtures/expected_report.md"
python main.py run "$SAMPLE_DIR" --report "$OUTPUT_REPORT"

if [ ! -f "$EXPECTED_REPORT" ]; then
  echo "Expected report file missing: $EXPECTED_REPORT"
  exit 1
fi

git diff --no-index -- "$EXPECTED_REPORT" "$OUTPUT_REPORT"
