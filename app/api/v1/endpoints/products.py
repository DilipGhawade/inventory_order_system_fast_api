from fastapi import APIRouter, Query, Response, status

from app.api.deps import AdminUserDep, DBSessionDep
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])


@router.get(
    "",
    response_model=PaginatedProductResponse,
    status_code=status.HTTP_200_OK,
    summary="List products with pagination and search filters",
)
async def list_products(
    db: DBSessionDep,
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=20, ge=1, le=100, description="Page size"),
    search: str | None = Query(default=None, max_length=100, description="Search by name, SKU, or description"),
    active_only: bool = Query(default=True, description="Filter only active products"),
    in_stock_only: bool = Query(default=False, description="Filter only products with stock greater than 0"),
) -> PaginatedProductResponse:
    return await ProductService.list_products(
        db=db,
        page=page,
        size=size,
        search=search,
        active_only=active_only,
        in_stock_only=in_stock_only,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a single product by ID",
)
async def get_product(
    product_id: int,
    db: DBSessionDep,
) -> ProductResponse:
    product = await ProductService.get_by_id(db=db, product_id=product_id)
    return ProductResponse.model_validate(product)


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new product in catalog (Admin only)",
)
async def create_product(
    product_in: ProductCreate,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> ProductResponse:
    product = await ProductService.create_product(db=db, product_in=product_in)
    return ProductResponse.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update product details or stock quantity (Admin only)",
)
async def update_product(
    product_id: int,
    product_in: ProductUpdate,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> ProductResponse:
    product = await ProductService.update_product(
        db=db,
        product_id=product_id,
        product_in=product_in,
    )
    return ProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete (deactivate) a product (Admin only)",
)
async def delete_product(
    product_id: int,
    db: DBSessionDep,
    _admin: AdminUserDep,
) -> Response:
    await ProductService.delete_product(db=db, product_id=product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)