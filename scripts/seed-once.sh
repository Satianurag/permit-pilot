#!/usr/bin/env bash
# One-time: load real NYC reference cases into Firestore (live Socrata pulls).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0233250350}"
cd "$ROOT/services/api"
exec .venv/bin/python -c "
import asyncio
from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore
from permit_pilot_core.seeds import ensure_seeded

async def main():
    store = FirestoreStore(project_id='$GOOGLE_CLOUD_PROJECT')
    engine = DistributionEngine()
    await ensure_seeded(store, engine)
    print('Seeded real NYC reference cases (if missing).')

asyncio.run(main())
"
