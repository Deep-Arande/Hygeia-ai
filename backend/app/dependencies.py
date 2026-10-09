"""Shared FastAPI dependencies — notably, resolving the authenticated user."""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .db import get_db
from .models import User
from .security import decode_access_token

# tokenUrl is where clients obtain a token (used by the /docs "Authorize" button).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if subject is None:
            raise credentials_exc
    except jwt.PyJWTError as exc:
        raise credentials_exc from exc

    user = db.get(User, int(subject))
    if user is None:
        raise credentials_exc
    return user
