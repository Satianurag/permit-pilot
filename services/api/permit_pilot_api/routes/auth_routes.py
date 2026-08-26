from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from permit_pilot_api.auth import ClerkUser, Token, authenticate_user, create_access_token, get_current_user
from permit_pilot_api.login_security import clear_failures, is_login_locked, record_failed_login

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    if is_login_locked(form_data.username):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Wait 15 minutes and try again.",
        )
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        record_failed_login(form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    clear_failures(form_data.username)
    token = create_access_token(username=user.username, role=user.role)
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=ClerkUser)
async def read_current_user(current_user: Annotated[ClerkUser, Depends(get_current_user)]) -> ClerkUser:
    return current_user
