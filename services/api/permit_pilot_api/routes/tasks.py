from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from permit_pilot_api.auth import ClerkUser, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/tasks", tags=["tasks"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_tasks(
    request: Request,
    status: Annotated[str | None, Query(description="Filter by task status")] = "open",
    assignee: Annotated[str | None, Query(description="Filter by assignee username")] = None,
    mine: Annotated[bool, Query(description="Only tasks assigned to the current user")] = False,
    unassigned: Annotated[bool, Query(description="Only tasks with no assignee")] = False,
    limit: Annotated[int, Query(ge=1, le=500, description="Max tasks to return")] = 100,
    offset: Annotated[int, Query(ge=0, description="Skip tasks for pagination")] = 0,
    current_user=Depends(get_current_user),
):
    store = store_from_request(request)
    if status == "all":
        status = None
    effective_assignee = current_user.username if mine else assignee
    return store.list_tasks(
        status=status,
        assignee=effective_assignee,
        unassigned_only=unassigned,
        limit=limit,
        offset=offset,
    )


@router.post("/{task_id}/claim")
def claim_task(
    task_id: str,
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    task = store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != "open":
        raise HTTPException(status_code=409, detail="Only open tasks can be claimed")
    if task.assignee and task.assignee != current_user.username:
        raise HTTPException(status_code=409, detail="Task is already assigned to another clerk")
    updated = store.assign_task(task_id, current_user.username)
    if not updated:
        raise HTTPException(status_code=404, detail="Task not found")
    return updated
