from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUserDep, DBSessionDep
from app.schemas.order import OrderCreate, OrderResponse, PaginatedOrderResponse
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order with atomic stock verification and deduction",
)
async def create_order(
    order_in: OrderCreate,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> OrderResponse:
    order = await OrderService.create_order(
        db=db,
        current_user=current_user,
        order_in=order_in,
    )
    return OrderResponse.model_validate(order)


@router.get(
    "",
    response_model=PaginatedOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="List paginated orders for current user (or all users if Admin requests all_users=true)",
)
async def list_orders(
    db: DBSessionDep,
    current_user: CurrentUserDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    all_users: bool = Query(default=False, description="When true and caller is Admin, returns all orders"),
) -> PaginatedOrderResponse:
    return await OrderService.list_orders(
        db=db,
        current_user=current_user,
        page=page,
        size=size,
        all_users=all_users,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get order details by ID",
)
async def get_order(
    order_id: int,
    db: DBSessionDep,
    current_user: CurrentUserDep,
) -> OrderResponse:
    order = await OrderService.get_order_by_id(
        db=db,
        order_id=order_id,
        current_user=current_user,
    )
    return OrderResponse.model_validate(order)