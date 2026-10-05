---
applyTo: "shopmind_api/**"
---
# ShopMind Commerce Backend — Copilot Instructions

## Purpose and stack
ShopMind is a single-merchant learning/portfolio commerce project. This module is the source of truth for commerce rules, authentication, authorization, transactions and data integrity.

Follow the repository's existing Python 3.12, FastAPI, PostgreSQL 17, Docker Compose, SQLAlchemy 2, Alembic, Pydantic v2, pytest, Ruff and uv setup. Inspect actual versions/configuration before changing dependencies.

## Existing implementation (from the latest project handoff)
The backend handoff records:
- Categories/products; product listing, pagination, filtering, search and sorting.
- Inventory management; customers and cart operations.
- Checkout, orders and order-item snapshots.
- Simulated payment gateway with success, failure and retry scenarios.
- Inventory deduction after successful payment; cart clearing after successful payment.
- Customer registration, login and current-user endpoint (`POST /auth/register`, `POST /auth/login`, `GET /auth/me`).
- Customer/admin roles; Argon2 password hashing; JWT access tokens; authenticated-user and admin dependencies; ownership checks; active-account verification.
- Controlled CLI/bootstrap for initial admin creation.
- Rotating application and audit logs with timestamps, severity and correlation IDs.

Tables recorded in the handoff: `categories`, `products`, `inventory`, `customers`, `cart_items`, `orders`, `order_items`, `payments`. Seed data recorded: about 500 products, 10 customers and 18 cart items.

The handoff reported 32 focused tests passing plus lint/format and PostgreSQL smoke checks. Treat these as historical reported results, not verified current results. Inspect the code and run checks before claiming anything. If code and handoff differ, code/tests/migrations are authoritative.

## Architecture rules
- Keep the existing separation of routers, schemas, services, repositories and ORM models. Follow actual repository layout.
- Business rules live in backend services/domain logic, never in MCP handlers or AI prompts.
- PostgreSQL is the source of truth. No direct DB access from MCP or AI.
- Use Alembic for schema changes; create new migrations for applied-schema changes.
- Use Pydantic v2 at API boundaries; do not leak ORM/internal fields.
- Preserve API contracts unless a change is explicitly requested.
- Keep transaction boundaries explicit. Explain commit, rollback and failure behavior for multi-step writes.
- Do not add Redis, Celery, Kubernetes, AWS or unrelated infrastructure ahead of the roadmap.
- Payments remain simulated; do not integrate a real payment provider.

## Authorization and customer safety
Only two roles currently exist: `admin` and `customer`.
- Customers manage only their own carts and orders.
- Customers cannot modify inventory or perform admin operations.
- Admins may perform the administrative operations already defined by the backend.
- Public catalogue/inventory reads remain public only where current routes specify.
- Registration must never allow self-assignment of `admin`.
- Initial admin creation uses the controlled bootstrap flow.
- Derive identity and role from a verified principal/token, never request fields or LLM arguments.
- Enforce ownership in the backend on every protected operation. Client-side hiding is not authorization.
- Preserve active-account checks.
- Return safe errors; do not leak secrets or unnecessary record/account existence information.

## Checkout and payment boundary
Preserve order snapshots and the existing payment → inventory deduction → cart-clearing invariants. Make retries safe and prevent duplicate side effects with idempotency where appropriate. Never send raw card data to an LLM or expose it as MCP arguments. Never store/log card number, CVV or expiry. Payment details belong in a dedicated payment UI/API flow. Consequential checkout requires explicit customer confirmation.

## AI/MCP boundaries
- MCP calls approved FastAPI endpoints through an HTTP client. It must not import commerce repositories/models or connect to PostgreSQL.
- AI workflows use approved commerce APIs; they do not bypass backend authorization.
- Backend authorization must remain effective when APIs are called directly, without MCP or an LLM.
- Propagated identity must be independently verifiable by FastAPI. Never trust model-supplied `user_id`, `role` or `is_admin`.

## Engineering expectations
Read nearby code/tests first. Match existing naming, DI, async/sync and error-handling conventions. Add tests for validation, authentication, wrong role, cross-customer ownership, success/failure and rollback. Use deterministic, relationally valid fixtures with meaningful edge cases. Bound pagination and allowlist sortable/filterable fields. Use timeouts for outbound HTTP; retry only safe/idempotent calls with bounded backoff. Propagate correlation IDs. Never log passwords, JWTs, secrets, card data or unnecessary PII.

Before coding, state the small intended change and affected layers. Ask one focused question if a material requirement is unclear. Avoid unrelated refactors. Report only tests/checks actually run. After implementation, explain authentication, role checks, ownership, transaction boundaries and rollback behavior.
