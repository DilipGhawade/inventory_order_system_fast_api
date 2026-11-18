from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0, description="ID of the product to purchase")
    quantity: int = Field(gt=0, le=10_000, description="Number of units to purchase")


class OrderCreate(BaseModel):
    shipping_address: str = Field(
        min_length=10,
        max_length=500,
        description="Full destination shipping address",
    )
    items: list[OrderItemCreate] = Field(
        min_length=1,
        max_length=100,
        description="Non-empty list of order line items",
    )

    @model_validator(mode="after")
    def check_unique_products(self) -> "OrderCreate":
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError(
                "Duplicate product_id entries found in order items. Consolidate quantities per product."
            )
        return self


class OrderItemProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    product: OrderItemProductSummary | None = None


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_address: str
    items: list[OrderItemResponse]
    created_at: datetime
    updated_at: datetime


class PaginatedOrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[OrderResponse]
    total: int
    page: int
    size: int
    pages: int