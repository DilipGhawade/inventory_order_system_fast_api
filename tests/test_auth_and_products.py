from decimal import Decimal
from httpx import AsyncClient
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from app.schemas.user import UserAdminCreate
from app.services.user_service import UserService

pytestmark = pytest.mark.asyncio


async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["database"] == "connected"


async def test_user_registration_login_and_refresh_flow(client: AsyncClient) -> None:
    register_payload = {
        "email": "customer@example.com",
        "full_name": "Alice Customer",
        "password": "SecurePassword123",
    }
    reg_response = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_response.status_code == 201
    user_data = reg_response.json()
    assert user_data["email"] == "customer@example.com"
    assert user_data["role"] == "user"

    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": "customer@example.com", "password": "SecurePassword123"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me_response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "customer@example.com"

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    assert "access_token" in refresh_response.json()


async def test_admin_product_crud_and_order_stock_deduction(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    admin_in = UserAdminCreate(
        email="admin@example.com",
        full_name="System Admin",
        password="AdminPassword123",
        role=UserRole.ADMIN,
        is_active=True,
    )
    await UserService.register_user(db=db_session, user_in=admin_in)

    login_resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@example.com", "password": "AdminPassword123"},
    )
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    product_payload = {
        "sku": "macbook-pro-16",
        "name": "MacBook Pro 16-inch M4",
        "description": "Enterprise workstation laptop",
        "price": "2499.50",
        "stock_quantity": 10,
        "is_active": True,
    }
    create_prod_resp = await client.post(
        "/api/v1/products",
        json=product_payload,
        headers=admin_headers,
    )
    assert create_prod_resp.status_code == 201
    created_product = create_prod_resp.json()
    product_id = created_product["id"]
    assert created_product["sku"] == "MACBOOK-PRO-16"
    assert created_product["stock_quantity"] == 10

    list_resp = await client.get("/api/v1/products?search=MacBook&page=1&size=10")
    assert list_resp.status_code == 200
    paginated = list_resp.json()
    assert paginated["total"] == 1
    assert len(paginated["items"]) == 1

    order_payload = {
        "shipping_address": "742 Evergreen Terrace, Springfield, IL 62701",
        "items": [{"product_id": product_id, "quantity": 3}],
    }
    order_resp = await client.post(
        "/api/v1/orders",
        json=order_payload,
        headers=admin_headers,
    )
    assert order_resp.status_code == 201
    order_data = order_resp.json()
    assert Decimal(order_data["total_amount"]) == Decimal("7498.50")
    assert order_data["items"][0]["quantity"] == 3

    updated_prod_resp = await client.get(f"/api/v1/products/{product_id}")
    assert updated_prod_resp.status_code == 200
    assert updated_prod_resp.json()["stock_quantity"] == 7

    excess_order_payload = {
        "shipping_address": "742 Evergreen Terrace, Springfield, IL 62701",
        "items": [{"product_id": product_id, "quantity": 50}],
    }
    excess_resp = await client.post(
        "/api/v1/orders",
        json=excess_order_payload,
        headers=admin_headers,
    )
    assert excess_resp.status_code == 400
    assert excess_resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"