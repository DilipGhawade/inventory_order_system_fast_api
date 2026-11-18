from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)

DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
TokenDep = Annotated[str | None, Depends(oauth2_scheme)]


async def get_current_user(
    db: DBSessionDep,
    token: TokenDep,
) -> User:
    """Resolve and validate the current authenticated user from the Bearer JWT."""
    if not token:
        raise AuthenticationError(detail="Authentication credentials were not provided.")

    payload = decode_token(token, expected_type="access")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError(detail="Invalid user identifier in token.") from exc

    user = await UserService.get_by_id(db, user_id)
    if user is None:
        raise AuthenticationError(detail="User account was not found.")
    if not user.is_active:
        raise AuthenticationError(detail="User account is disabled.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def get_current_active_admin(
    current_user: CurrentUserDep,
) -> User:
    """Verify that the current authenticated user holds the ADMIN role."""
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedError(detail="Administrator privileges are required for this resource.")
    return current_user


AdminUserDep = Annotated[User, Depends(get_current_active_admin)]