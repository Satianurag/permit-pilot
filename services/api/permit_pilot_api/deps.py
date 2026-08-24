from fastapi import Request

from permit_pilot_core.distribution.engine import DistributionEngine
from permit_pilot_core.firestore.store import FirestoreStore


def store_from_request(request: Request) -> FirestoreStore:
    return request.app.state.store


def engine_from_request(request: Request) -> DistributionEngine:
    return request.app.state.engine
