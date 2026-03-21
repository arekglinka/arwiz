#!/usr/bin/env bash
# arwiz FastAPI endpoint examples
#
# Start the server first:
#   uvicorn arwiz.api:app --reload
#
# All endpoints live at http://localhost:8000

set -euo pipefail

BASE="http://localhost:8000"
SCRIPT="examples/01_quickstart.py"

echo "=== Health Check ==="
curl -s "$BASE/health" | python -m json.tool

echo ""
echo "=== Profile a Script ==="
curl -s -X POST "$BASE/profile" \
  -H "Content-Type: application/json" \
  -d "{\"script_path\": \"$SCRIPT\"}" \
  | python -m json.tool

echo ""
echo "=== Optimize a Function ==="
curl -s -X POST "$BASE/optimize" \
  -H "Content-Type: application/json" \
  -d "{\"script_path\": \"$SCRIPT\", \"function_name\": \"compute_sum\"}" \
  | python -m json.tool

echo ""
echo "=== Trace Branch Coverage ==="
curl -s -X POST "$BASE/coverage" \
  -H "Content-Type: application/json" \
  -d "{\"script_path\": \"$SCRIPT\"}" \
  | python -m json.tool
