from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from permit_pilot_core.models import ActivityFeed
from permit_pilot_api.auth import get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/activity", tags=["activity"], dependencies=[Depends(get_current_user)])


@router.get("")
def list_activity(
    request: Request,
    limit: Annotated[int, Query(ge=1, le=200, description="Max events to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Skip events for pagination")] = 0,
    action: Annotated[str | None, Query(description="Filter by audit action")] = None,
) -> ActivityFeed:
    store = store_from_request(request)
    items, total = store.list_recent_activity(limit=limit, offset=offset, action=action)
    actions = store.list_audit_actions()
    return ActivityFeed(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        actions=actions,
    )
