from decimal import Decimal
import math

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import (
    EntityNotFoundError,
    InsufficientStockError,
    PermissionDeniedError,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole
from app.schemas.order import OrderCreate, OrderResponse, PaginatedOrderResponse


class OrderService:
    """Service layer managing transactional order creation and stock reservation."""

    @staticmethod
    async def create_order(
        db: AsyncSession,
        current_user: User,
        order_in: OrderCreate,
    ) -> Order:
        requested_map: dict[int, int] = {
            item.product_id: item.quantity for item in order_in.items
        }
        sorted_product_ids = sorted(requested_map.keys())

        stmt = (
            select(Product)
            .where(Product.id.in_(sorted_product_ids))
            .order_by(Product.id.asc())
            .with_for_update()
        )
        result = await db.execute(stmt)
        products = list(result.scalars().all())
        product_lookup: dict[int, Product] = {p.id: p for p in products}

        for pid in sorted_product_ids:
            product = product_lookup.get(pid)
            if product is None or not product.is_active:
                raise EntityNotFoundError(
                    detail=f"Product with ID {pid} does not exist or is inactive."
                )
            requested_qty = requested_map[pid]
            if product.stock_quantity < requested_qty:
                raise InsufficientStockError(
                    detail=(
                        f"Insufficient stock for product '{product.name}' (SKU: {product.sku}). "
                        f"Requested: {requested_qty}, Available: {product.stock_quantity}."
                    )
                )

        total_amount = Decimal("0.00")
        order_items: list[OrderItem] = []

        for pid in sorted_product_ids:
            product = product_lookup[pid]
            quantity = requested_map[pid]
            product.stock_quantity -= quantity

            subtotal = (product.price * Decimal(quantity)).quantize(Decimal("0.01"))
            total_amount += subtotal

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                    subtotal=subtotal,
                )
            )

        new_order = Order(
            user_id=current_user.id,
            status=OrderStatus.CONFIRMED,
            total_amount=total_amount,
            shipping_address=order_in.shipping_address.strip(),
            items=order_items,
        )
        db.add(new_order)
        await db.commit()

        reload_stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == new_order.id)
        )
        reloaded_result = await db.execute(reload_stmt)
        return reloaded_result.scalar_one()

    @staticmethod
    async def get_order_by_id(
        db: AsyncSession,
        order_id: int,
        current_user: User,
    ) -> Order:
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == order_id)
        )
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            raise EntityNotFoundError(detail=f"Order with ID {order_id} was not found.")

        if current_user.role != UserRole.ADMIN and order.user_id != current_user.id:
            raise PermissionDeniedError(detail="You are not authorized to view this order.")

        return order

    @staticmethod
    async def list_orders(
        db: AsyncSession,
        current_user: User,
        page: int = 1,
        size: int = 20,
        all_users: bool = False,
    ) -> PaginatedOrderResponse:
        filters = []
        if not (all_users and current_user.role == UserRole.ADMIN):
            filters.append(Order.user_id == current_user.id)

        count_stmt = select(func.count(Order.id)).where(*filters)
        total_result = await db.execute(count_stmt)
        total = int(total_result.scalar_one() or 0)

        offset = (page - 1) * size
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(*filters)
            .order_by(Order.created_at.desc(), Order.id.desc())
            .offset(offset)
            .limit(size)
        )
        result = await db.execute(stmt)
        orders = list(result.scalars().all())

        pages = math.ceil(total / size) if total > 0 else 0
        return PaginatedOrderResponse(
            items=[OrderResponse.model_validate(o) for o in orders],
            total=total,
            page=page,
            size=size,
            pages=pages,
        )