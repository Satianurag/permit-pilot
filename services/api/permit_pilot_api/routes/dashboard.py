from typing import Annotated

from fastapi import APIRouter, Depends, Request

from permit_pilot_api.auth import ClerkUser, get_current_user
from permit_pilot_api.deps import store_from_request

router = APIRouter(prefix="/dashboard", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/summary")
def dashboard_summary(
    request: Request,
    current_user: Annotated[ClerkUser, Depends(get_current_user)],
):
    store = store_from_request(request)
    return store.dashboard_summary(username=current_user.username)
