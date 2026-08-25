from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from permit_pilot_api.auth import get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_tasks(
    request: Request,
    status: Annotated[str | None, Query(description="Filter by task status")] = "open",
    assignee: Annotated[str | None, Query(description="Filter by assignee username")] = None,
    mine: Annotated[bool, Query(description="Only tasks assigned to the current user")] = False,
    current_user=Depends(get_current_user),
):
    store = store_from_request(request)
    if status == "all":
        status = None
    effective_assignee = current_user.username if mine else assignee
    return store.list_tasks(status=status, assignee=effective_assignee)
