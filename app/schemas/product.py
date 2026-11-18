from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductBase(BaseModel):
    sku: str = Field(
        min_length=3,
        max_length=64,
        pattern=r"^[A-Za-z0-9\-_]+$",
        description="Unique alphanumeric SKU identifier",
    )
    name: str = Field(min_length=2, max_length=200, description="Product display name")
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal = Field(ge=Decimal("0.00"), max_digits=12, decimal_places=2)
    stock_quantity: int = Field(default=0, ge=0, le=1_000_000)
    is_active: bool = Field(default=True)

    @field_validator("sku")
    @classmethod
    def normalize_sku(cls, v: str) -> str:
        return v.strip().upper()


class ProductCreate(ProductBase):
    """Schema for creating a new product in inventory."""


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: Decimal | None = Field(default=None, ge=Decimal("0.00"), max_digits=12, decimal_places=2)
    stock_quantity: int | None = Field(default=None, ge=0, le=1_000_000)
    is_active: bool | None = None


class ProductResponse(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PaginatedProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[ProductResponse]
    total: int = Field(ge=0, description="Total matching records in database")
    page: int = Field(ge=1, description="Current page number (1-indexed)")
    size: int = Field(ge=1, description="Number of items per page")
    pages: int = Field(ge=0, description="Total number of pages")