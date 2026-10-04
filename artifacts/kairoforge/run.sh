#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
PORT="${PORT:-26067}"
DOMAIN="${REPLIT_DOMAINS:-localhost}"
DOMAIN="${DOMAIN%%,*}"

cd "$WORKSPACE_ROOT"

exec streamlit run "$WORKSPACE_ROOT/app.py" \
  --server.port "$PORT" \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false \
  --browser.serverAddress "$DOMAIN" \
  --browser.serverPort "$PORT" \
  --browser.gatherUsageStats false
