from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DBSessionDep
from app.schemas.token import RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new standard user account",
)
async def register(
    user_in: UserCreate,
    db: DBSessionDep,
) -> UserResponse:
    user = await UserService.register_user(db=db, user_in=user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate with email and password to obtain JWT access and refresh tokens",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DBSessionDep,
) -> TokenResponse:
    return await UserService.authenticate(
        db=db,
        email=form_data.username,
        password=form_data.password,
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a valid refresh token for a new token pair",
)
async def refresh_access_token(
    body: RefreshTokenRequest,
    db: DBSessionDep,
) -> TokenResponse:
    return await UserService.refresh_tokens(db=db, refresh_token=body.refresh_token)