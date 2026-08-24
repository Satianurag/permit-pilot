from fastapi import APIRouter, Request

from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("")
def list_tasks(request: Request):
    store = store_from_request(request)
    return store.list_tasks()
