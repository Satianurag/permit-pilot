from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from permit_pilot_api.auth import get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_tasks(
    request: Request,
    status: Annotated[str | None, Query(description="Filter by task status")] = "open",
):
    store = store_from_request(request)
    return store.list_tasks(status=status)
