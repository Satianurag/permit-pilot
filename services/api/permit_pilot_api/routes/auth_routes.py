from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from permit_pilot_api.auth import ClerkUser, Token, authenticate_user, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/token", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(username=user.username, role=user.role)
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=ClerkUser)
async def read_current_user(current_user: Annotated[ClerkUser, Depends(get_current_user)]) -> ClerkUser:
    return current_user
