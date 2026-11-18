from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    EntityNotFoundError,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.models.user import User, UserRole
from app.schemas.token import TokenResponse
from app.schemas.user import UserAdminCreate, UserCreate, UserUpdate


class UserService:
    """Service encapsulating user management, registration, and authentication workflows."""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        normalized_email = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def register_user(
        cls,
        db: AsyncSession,
        user_in: UserCreate | UserAdminCreate,
    ) -> User:
        existing_user = await cls.get_by_email(db, user_in.email)
        if existing_user is not None:
            raise ConflictError(detail=f"User with email '{user_in.email}' is already registered.")

        role = user_in.role if isinstance(user_in, UserAdminCreate) else UserRole.USER
        is_active = user_in.is_active if isinstance(user_in, UserAdminCreate) else True

        new_user = User(
            email=user_in.email.strip().lower(),
            full_name=user_in.full_name.strip(),
            hashed_password=get_password_hash(user_in.password),
            role=role,
            is_active=is_active,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        return new_user

    @classmethod
    async def authenticate(
        cls,
        db: AsyncSession,
        email: str,
        password: str,
    ) -> TokenResponse:
        user = await cls.get_by_email(db, email)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError(detail="Incorrect email or password.")

        if not user.is_active:
            raise AuthenticationError(detail="User account is inactive.")

        return cls.issue_tokens(user)

    @classmethod
    async def refresh_tokens(
        cls,
        db: AsyncSession,
        refresh_token: str,
    ) -> TokenResponse:
        payload = decode_token(refresh_token, expected_type="refresh")
        user_id = int(payload["sub"])
        user = await cls.get_by_id(db, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError(detail="User associated with token no longer exists or is inactive.")

        return cls.issue_tokens(user)

    @staticmethod
    def issue_tokens(user: User) -> TokenResponse:
        access_token = create_access_token(subject=user.id, role=user.role.value)
        refresh_token = create_refresh_token(subject=user.id, role=user.role.value)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @staticmethod
    async def list_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> list[User]:
        stmt = select(User).order_by(User.id.asc()).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    async def update_user(
        cls,
        db: AsyncSession,
        user_id: int,
        user_in: UserUpdate,
    ) -> User:
        user = await cls.get_by_id(db, user_id)
        if user is None:
            raise EntityNotFoundError(detail=f"User with ID {user_id} was not found.")

        update_data = user_in.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"] is not None:
            user.hashed_password = get_password_hash(update_data.pop("password"))

        for field, value in update_data.items():
            setattr(user, field, value)

        await db.commit()
        await db.refresh(user)
        return user