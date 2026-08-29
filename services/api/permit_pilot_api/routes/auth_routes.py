from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, Field

from permit_pilot_api.auth import ClerkUser, Token, authenticate_user, create_access_token, get_current_user
from permit_pilot_api.clerk_accounts import upsert_google_clerk
from permit_pilot_api.login_security import clear_failures, is_login_locked, record_failed_login
from permit_pilot_core.settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class GoogleCredential(BaseModel):
    credential: str = Field(min_length=20)


@router.get("/google-client")
async def google_client() -> dict[str, str]:
    return {"client_id": get_settings().google_signin_client_id}


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


@router.post("/google", response_model=Token)
async def google_login(body: GoogleCredential) -> Token:
    client_id = get_settings().google_signin_client_id.strip()
    if not client_id:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google Sign-In is not configured")
    try:
        info = google_id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            audience=client_id,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google sign-in could not be verified",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    email = str(info.get("email") or "").strip().lower()
    if not email or not info.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google account email is not verified")
    if is_login_locked(email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Wait 15 minutes and try again.",
        )
    name = str(info.get("name") or email)
    user = upsert_google_clerk(email=email, full_name=name)
    clear_failures(email)
    token = create_access_token(username=user.username, role=user.role)
    return Token(access_token=token, token_type="bearer")


@router.get("/me", response_model=ClerkUser)
async def read_current_user(current_user: Annotated[ClerkUser, Depends(get_current_user)]) -> ClerkUser:
    return current_user
