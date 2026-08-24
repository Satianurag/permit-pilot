#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

if [ -f "$ROOT/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  set +a
fi

gcloud config set project "$GOOGLE_CLOUD_PROJECT" >/dev/null 2>&1 || true

case "${1:-}" in
  api)
    cd "$ROOT/services/api"
    exec .venv/bin/uvicorn permit_pilot_api.main:app --reload --host 127.0.0.1 --port 8000
    ;;
  web)
    cd "$ROOT/web"
    exec npm run dev -- --host 127.0.0.1 --port 5173
    ;;
  *)
    echo "Usage: $0 {api|web}"
    exit 1
    ;;
esac
