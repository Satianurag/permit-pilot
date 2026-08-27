#!/usr/bin/env bash
# Seed NYC reference cases into Cloud Firestore (run after deploy).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROJECT="${GOOGLE_CLOUD_PROJECT:?Set GOOGLE_CLOUD_PROJECT}"
export GOOGLE_CLOUD_PROJECT="$PROJECT"

cd "$ROOT/services/api"
PYTHON="${ROOT}/services/api/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  PYTHON="python3"
fi

exec "$PYTHON" -c "
import asyncio
from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.seeds import ensure_seeded

async def main():
    store = FirestoreStore(project_id='${PROJECT}')
    engine = DistributionEngine()
    await ensure_seeded(store, engine)
    open_tasks = store.list_tasks(status='open')
    print(f'Cloud Firestore ready: {len(store.list_cases())} cases, {len(open_tasks)} open tasks')

asyncio.run(main())
"
