"""Authentication and server-side authorisation.

Authorisation is always enforced on the server (Definition of Done), never merely
hidden in the UI.

For this first slice, identity is a simplified `X-User` header carrying a known
handle — a stand-in for real session auth (OIDC) which is deliberately out of scope
for slice 1. Roles (contributor / curator / admin) gate privileged actions.
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Role, User


def get_current_user(
    x_user: str | None = Header(default=None, alias="X-User"),
    db: Session = Depends(get_db),
) -> User:
    if not x_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "not_authenticated", "message": "Sign in to contribute."},
        )
    user = db.scalar(select(User).where(User.handle == x_user))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unknown_user", "message": "Unknown or disabled account."},
        )
    return user


def require_curator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (Role.curator, Role.admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "forbidden",
                "message": "Only curators can moderate or archive records.",
            },
        )
    return user
