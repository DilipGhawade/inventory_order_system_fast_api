
### File: README.md

```markdown
# Enterprise Inventory & Order Management API

A production-ready, asynchronous RESTful API backend built with **Python 3.12+**, **FastAPI**, **SQLAlchemy 2.0 (Async)**, and **PostgreSQL 16**. Designed with clean layered architecture, strict Role-Based Access Control (RBAC), atomic inventory deduction, and structured JSON observability.

---

## Core Features & Architecture

- **Asynchronous Database Layer**: Powered by SQLAlchemy 2.0 (`Mapped` and `mapped_column` syntax) and `asyncpg` with connection pooling (`pool_pre_ping=True`).
- **Concurrency-Safe Order Engine**: Uses PostgreSQL row-level locking (`SELECT ... FOR UPDATE`) sorted by product ID to prevent race conditions, overselling, and database deadlocks under concurrent traffic.
- **JWT Authentication & RBAC**: Dual-secret JWT implementation (short-lived Access Tokens + long-lived Refresh Tokens), `bcrypt` password hashing, and granular role enforcement (`admin` vs. `user`).
- **Strict Data Validation**: Built on Pydantic v2 (`ConfigDict(from_attributes=True)`) and `pydantic-settings` for startup environment validation.
- **Async Database Migrations**: Configured with Alembic running over an asynchronous SQLAlchemy engine with automatic schema diffing.
- **Production Observability & Security**:
  - Structured JSON logging via `structlog` with per-request correlation IDs (`X-Request-ID`) and execution latency tracking (`X-Process-Time`).
  - Global domain exception handlers returning standardized JSON error payloads.
  - Security headers (`Strict-Transport-Security`, `X-Content-Type-Options`, `X-Frame-Options`), CORS, and Trusted Host middleware.
  - Automatic disabling of `/docs` and `/redoc` when `ENVIRONMENT=production`.

---

## Tech Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| Framework | FastAPI | 0.115.6 | High-performance async REST framework |
| Server | Uvicorn & Gunicorn | 0.34.0 / 23.0.0 | ASGI server and multi-worker process manager |
| ORM & Driver | SQLAlchemy & asyncpg | 2.0.36 / 0.30.0 | Async ORM and PostgreSQL wire-protocol driver |
| Migrations | Alembic | 1.14.0 | Database schema version control |
| Validation | Pydantic v2 | 2.10.4 | Request/response serialization and settings |
| Security | PyJWT & bcrypt | 2.10.1 / 4.2.1 | Token signing and password hashing |
| Logging | structlog | 24.4.0 | Structured JSON event logging |
| Testing | Pytest & HTTPX | 8.3.4 / 0.28.1 | Async integration testing suite |

---

## Project Directory Structure

```text
inventory_order_system/
├── .env.example                  # Template environment variables
├── Dockerfile                    # Multi-stage production Docker build (non-root user)
├── docker-compose.yml            # PostgreSQL 16 + FastAPI orchestration
├── alembic.ini                   # Alembic CLI configuration
├── requirements.txt              # Pinned Python dependencies
├── alembic/
│   ├── env.py                    # Async SQLAlchemy migration environment
│   ├── script.py.mako            # Migration file generation template
│   └── versions/                 # Generated schema migration scripts
├── app/
│   ├── main.py                   # FastAPI app factory, lifespan, middleware & /health
│   ├── api/
│   │   ├── deps.py               # Annotated dependencies (DB session, JWT auth, RBAC)
│   │   └── v1/
│   │       ├── router.py         # API v1 master router
│   │       └── endpoints/
│   │           ├── auth.py       # /register, /login, /refresh
│   │           ├── users.py      # /me and Admin user management
│   │           ├── products.py   # Paginated catalog & Admin inventory CRUD
│   │           └── orders.py     # Transactional order placement & history
│   ├── core/
│   │   ├── config.py             # Pydantic BaseSettings (.env loader)
│   │   ├── exceptions.py         # Custom domain errors & global handlers
│   │   ├── logging.py            # structlog JSON & console configuration
│   │   └── security.py           # Bcrypt hashing & JWT encode/decode
│   ├── db/
│   │   ├── base.py               # DeclarativeBase with id, created_at, updated_at
│   │   └── session.py            # Async engine, pool config & get_db generator
│   ├── models/
│   │   ├── user.py               # User ORM model & UserRole enum
│   │   ├── product.py            # Product ORM model with check constraints
│   │   └── order.py              # Order & OrderItem ORM models
│   ├── schemas/
│   │   ├── token.py              # JWT response & refresh schemas
│   │   ├── user.py               # User CRUD & response schemas
│   │   ├── product.py            # Product CRUD & pagination schemas
│   │   └── order.py              # Order creation & receipt schemas
│   └── services/
│       ├── user_service.py       # Registration, authentication & user CRUD logic
│       ├── product_service.py    # Catalog filtering, pagination & stock updates
│       └── order_service.py      # Atomic order creation & stock reservation
└── tests/
    ├── conftest.py               # Async test engine & HTTPX client fixtures
    └── test_auth_and_products.py # End-to-end integration tests

```

---

## Local Development Setup

### Prerequisites

* **Python 3.12+**
* **PostgreSQL 16** (running locally or via Docker Desktop)

### 1. Create and Activate Virtual Environment

```bash
python3 -m venv env
source env/bin/activate

```

### 2. Install Dependencies

```bash
./env/bin/python -m pip install --upgrade pip
./env/bin/python -m pip install -r requirements.txt

```

### 3. Configure Environment Variables

```bash
cp .env.example .env

```

### 4. Start PostgreSQL Database

**Option A — Using Docker Compose (Recommended):**

```bash
docker compose up -d db

```

**Option B — Using Local macOS/Linux PostgreSQL:**

```bash
psql -d template1 -c "CREATE USER inventory_user WITH PASSWORD 'inventory_secure_password' CREATEDB;"
psql -d template1 -c "CREATE DATABASE inventory_db OWNER inventory_user;"

```

### 5. Run Database Migrations

```bash
# Generate initial schema migration
./env/bin/python -m alembic revision --autogenerate -m "initial_inventory_order_schema"

# Apply migrations to PostgreSQL
./env/bin/python -m alembic upgrade head

```

### 6. Start the FastAPI Server

```bash
./env/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

* **API Base URL**: `http://127.0.0.1:8000/api/v1`
* **Interactive Swagger UI**: `http://127.0.0.1:8000/docs`
* **ReDoc Documentation**: `http://127.0.0.1:8000/redoc`
* **Health Readiness Probe**: `http://127.0.0.1:8000/health`

---

## Running with Docker Compose (Production Mode)

To build the multi-stage Docker image (running Gunicorn with 4 Uvicorn workers under a non-root user) alongside PostgreSQL 16:

```bash
docker compose up --build -d

```

Run migrations inside the running API container:

```bash
docker compose exec api alembic upgrade head

```

Check container health and logs:

```bash
docker compose ps
docker compose logs -f api

```

---

## API Endpoints Reference

| Method | Endpoint | Access | Description |
| --- | --- | --- | --- |
| GET | /health | Public | Verifies API status and PostgreSQL connectivity |
| POST | /api/v1/auth/register | Public | Registers a new user account |
| POST | /api/v1/auth/login | Public | Authenticates via form data and returns JWT pair |
| POST | /api/v1/auth/refresh | Public | Exchanges refresh token for a new JWT pair |
| GET | /api/v1/users/me | Authenticated | Returns current logged-in user profile |
| GET | /api/v1/users | Admin | Lists all registered users (paginated) |
| POST | /api/v1/users | Admin | Creates a user with explicit role and active flag |
| GET | /api/v1/users/{user_id} | Admin | Retrieves user details by ID |
| PATCH | /api/v1/users/{user_id} | Admin | Updates user details, password, role, or status |
| GET | /api/v1/products | Public | Lists products with pagination, search, and stock filters |
| GET | /api/v1/products/{product_id} | Public | Retrieves single product details |
| POST | /api/v1/products | Admin | Creates a new product in inventory |
| PATCH | /api/v1/products/{product_id} | Admin | Updates product price, stock quantity, or details |
| DELETE | /api/v1/products/{product_id} | Admin | Soft-deletes (deactivates) a product |
| POST | /api/v1/orders | Authenticated | Places an order with atomic stock verification |
| GET | /api/v1/orders | Authenticated | Lists user orders (or all orders if Admin sets `all_users=true`) |
| GET | /api/v1/orders/{order_id} | Authenticated | Retrieves full order receipt and line items |

---

## Standard Error Response Format

All domain, validation, and database integrity errors return a consistent JSON structure:

```json
{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for product 'MacBook Pro 16-inch M4' (SKU: MBP-16-M4). Requested: 50, Available: 7.",
    "path": "/api/v1/orders"
  }
}

```

---

## Running the Automated Test Suite

The test suite uses `pytest-asyncio`, `httpx.AsyncClient`, and an isolated in-memory database override so tests run quickly without modifying development data:

```bash
./env/bin/python -m pytest -v

```

---

## Key Environment Variables

| Variable | Default | Description |
| --- | --- | --- |
| ENVIRONMENT | development | Runtime mode (`development`, `staging`, `production`, `testing`) |
| SECRET_KEY | (32+ char hex) | Secret key used to sign JWT access tokens |
| REFRESH_SECRET_KEY | (32+ char hex) | Secret key used to sign JWT refresh tokens |
| ACCESS_TOKEN_EXPIRE_MINUTES | 30 | Lifespan of access tokens in minutes |
| REFRESH_TOKEN_EXPIRE_DAYS | 7 | Lifespan of refresh tokens in days |
| DATABASE_URL | postgresql+asyncpg://... | Async SQLAlchemy PostgreSQL connection string |
| DB_POOL_SIZE | 20 | Number of persistent connections kept in pool |
| DB_MAX_OVERFLOW | 10 | Max burst connections allowed above pool size |
| CORS_ORIGINS | ["http://localhost:3000"] | Allowed frontend origins for CORS |
| LOG_JSON_FORMAT | true | Outputs structured JSON logs when true |

```

```
