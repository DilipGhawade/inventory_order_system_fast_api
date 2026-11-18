import math
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, EntityNotFoundError
from app.models.product import Product
from app.schemas.product import (
    PaginatedProductResponse,
    ProductCreate,
    ProductResponse,
    ProductUpdate,
)


class ProductService:
    """Service layer handling product inventory CRUD, filtering, and pagination."""

    @staticmethod
    async def get_by_id(db: AsyncSession, product_id: int) -> Product:
        stmt = select(Product).where(Product.id == product_id)
        result = await db.execute(stmt)
        product = result.scalar_one_or_none()
        if product is None:
            raise EntityNotFoundError(detail=f"Product with ID {product_id} was not found.")
        return product

    @staticmethod
    async def get_by_sku(db: AsyncSession, sku: str) -> Product | None:
        normalized_sku = sku.strip().upper()
        stmt = select(Product).where(Product.sku == normalized_sku)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    async def create_product(
        cls,
        db: AsyncSession,
        product_in: ProductCreate,
    ) -> Product:
        existing = await cls.get_by_sku(db, product_in.sku)
        if existing is not None:
            raise ConflictError(detail=f"Product with SKU '{product_in.sku}' already exists.")

        product = Product(
            sku=product_in.sku,
            name=product_in.name.strip(),
            description=product_in.description,
            price=product_in.price,
            stock_quantity=product_in.stock_quantity,
            is_active=product_in.is_active,
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product

    @classmethod
    async def update_product(
        cls,
        db: AsyncSession,
        product_id: int,
        product_in: ProductUpdate,
    ) -> Product:
        product = await cls.get_by_id(db, product_id)
        update_data = product_in.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(product, field, value)

        await db.commit()
        await db.refresh(product)
        return product

    @classmethod
    async def delete_product(cls, db: AsyncSession, product_id: int) -> None:
        product = await cls.get_by_id(db, product_id)
        product.is_active = False
        await db.commit()

    @staticmethod
    async def list_products(
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        active_only: bool = True,
        in_stock_only: bool = False,
    ) -> PaginatedProductResponse:
        filters = []
        if active_only:
            filters.append(Product.is_active.is_(True))
        if in_stock_only:
            filters.append(Product.stock_quantity > 0)
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    Product.name.ilike(pattern),
                    Product.sku.ilike(pattern),
                    Product.description.ilike(pattern),
                )
            )

        count_stmt = select(func.count(Product.id)).where(*filters)
        total_result = await db.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        offset = (page - 1) * size
        items_stmt = (
            select(Product)
            .where(*filters)
            .order_by(Product.id.desc())
            .offset(offset)
            .limit(size)
        )
        items_result = await db.execute(items_stmt)
        products = list(items_result.scalars().all())

        pages = math.ceil(total / size) if total > 0 else 0
        return PaginatedProductResponse(
            items=[ProductResponse.model_validate(p) for p in products],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )