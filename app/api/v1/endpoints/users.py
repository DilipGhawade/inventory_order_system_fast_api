from fastapi import APIRouter, Query, status

from app.api.deps import AdminUserDep, CurrentUserDep, DBSessionDep
from app.core.exceptions import EntityNotFoundError
from app.schemas.user import UserAdminCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the profile of the currently authenticated user",
)
async def read_current_user(current_user: CurrentUserDep) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="List all registered users (Admin only)",
)
async def list_all_users(
    db: DBSessionDep,
    _admin: AdminUserDep,
    skip: int = Query(default=0, ge=0, description="Number of records to skip"),
    limit: int = Query(default=50, ge=1, le=200, description="Max records to return"),
) -> list[UserResponse]:
    users = await UserService.list_users(db=db, skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user with explicit role assignment (Admin only)",
)
async def create_user_by_admin(
    user_in: UserAdminCreate,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> UserResponse:
    user = await UserService.register_user(db=db, user_in=user_in)
    return UserResponse.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user details by ID (Admin only)",
)
async def get_user_by_id(
    user_id: int,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> UserResponse:
    user = await UserService.get_by_id(db=db, user_id=user_id)
    if user is None:
        raise EntityNotFoundError(detail=f"User with ID {user_id} was not found.")
    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user attributes, role, or status (Admin only)",
)
async def update_user_by_admin(
    user_id: int,
    user_in: UserUpdate,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> UserResponse:
    user = await UserService.update_user(db=db, user_id=user_id, user_in=user_in)
    return UserResponse.model_validate(user)