# shopmind
AI-powered commerce platform exploring RAG, tool calling, MCP, and agentic workflows.

## Inventory

Inventory tracks one stock quantity per product at a single logical location.

- `GET /inventory/{product_id}` returns
  `{"product_id": 1, "quantity": 5, "is_in_stock": true}`. Returns 404 if no
  inventory record exists, including for an unknown product.
- `PUT /inventory/{product_id}` requires an admin token, accepts `{"quantity": 5}` and creates or replaces
  the quantity, returning the same response shape with HTTP 200. The product must
  already exist; otherwise it returns 404.
- Quantity must be an integer from 0 through 2147483647 (the database integer
  limit). Invalid bodies or non-integer product IDs return 422.
- `is_in_stock` is read-only and derived from `quantity > 0`; zero means out of
  stock. Additional request fields are rejected.

The inventory table is defined by Alembic revision `61c13f798e24`, following
`8ecea52416d2`. The migration must be applied before using these endpoints.
There are no reservations, warehouses, stock movements, or automatic deductions.

## Customers and shopping cart

- `POST /auth/register` accepts
  `{"name": "Jane Doe", "email": "jane@example.com", "password": "strong-password"}`
  and returns the customer's `id`, `name`, `email`, and `created_at` with HTTP 201.
  Names are trimmed and must be nonempty. Emails are validated, trimmed, and
  normalized to lowercase. Duplicate emails return 409 and are also prevented
  by a database unique constraint.
- `GET /customers/{customer_id}` returns customer details or 404; only the owner
  or an admin can access it.
- `GET /cart/{customer_id}` returns `customer_id`, `items`, and `total`. Each item
  includes full `product` details, `quantity`, and `subtotal`. Existing customers
  start with an empty cart and a zero total; unknown customers return 404.
- `POST /cart/{customer_id}/items` accepts `{"product_id": 1, "quantity": 2}`.
  Adding an existing product increments its quantity.
- `PUT /cart/{customer_id}/items/{product_id}` accepts `{"quantity": 3}` and
  replaces the quantity of an existing item.
- `DELETE /cart/{customer_id}/items/{product_id}` removes an existing item.
  All successful cart mutations return the updated cart with HTTP 200.

Cart quantities must be positive integers within the database integer limit.
Malformed requests return 422. Missing customers, products, or cart items return
404. Inactive products and quantities exceeding current inventory return 409;
missing inventory is treated as unavailable. These checks apply when adding or
updating items. Removal remains possible for inactive or unavailable products.
Totals use current product prices and decimal arithmetic, serialized as strings.
There are no reservations or stock deductions, so availability may change after
an item is added; reading a cart does not silently remove or adjust its items.
There are no promotions, coupons, shipping calculations, or guest carts.
All cart operations require a customer token matching the URL's customer ID.
Admins cannot operate customer carts or check out/pay on behalf of customers.

### Migration instructions

Install the updated dependencies and, when ready, apply the migration from the
repository root with the intended database settings configured:

```sh
uv sync
uv run alembic upgrade head
```

Revision `7b824cdf09e1` follows inventory revision `61c13f798e24` and creates
`customers` and `cart_items`. The cart uses one item per customer/product pair;
no separate cart record is needed. To roll back only this revision (dropping all
customers and cart items), use `uv run alembic downgrade 61c13f798e24`.

## Checkout, orders, and payments

- `POST /checkout/{customer_id}` creates a pending order using a non-empty cart.
  The customer, active products, and current inventory are checked first.
  Product name, SKU, price, and quantity are copied into immutable order-item
  snapshots. Checkout does not reserve or deduct inventory.
- `POST /orders/{order_id}/payments` accepts
  `{"card_number":"4242424242424242","expiry_month":12,"expiry_year":2099,"cvv":"123"}`.
  Card number is validated with Luhn; expiry and three/four-digit CVV are
  validated before the mock gateway is called. Use a future expiry date.
  `4242424242424242` simulates success and
  `4000000000000002` simulates a declined payment; other valid Luhn numbers
  simulate failure. These are synthetic test values only.
- A successful payment locks and rechecks stock, deducts inventory atomically,
  confirms the order, and clears the customer's cart. A failed gateway attempt
  or insufficient stock records a failed attempt and retains both cart and
  inventory. A failed order can be retried on the same order; confirmed orders
  reject further payment attempts.
- `GET /orders/{order_id}` returns order details and item snapshots.
  `GET /customers/{customer_id}/orders?page=1&page_size=20` returns paginated
  order history. `GET /orders/{order_id}/payments` returns safe payment attempt
  metadata only.

Payment responses and the database contain only payment status, amount,
provider reference, card brand, and last four digits. Card number, CVV, and
expiry are never persisted or included in API responses. Never forward them to
LLM or MCP tools. The new schema is revision `b3f7c4d91a20`, after
`7b824cdf09e1`; follow-up revision `f4a19c6d2e83` permits zero-value orders.
Apply the schema with `uv run alembic upgrade head`.

## Authentication, authorization and logging

Authentication follows the existing route -> service -> repository and FastAPI
dependency-injection architecture. Argon2id hashes are stored in `customers`;
neither hashes nor passwords appear in profile responses. Registration accepts
only name, email and password (8-1024 characters); unknown fields, including
`role`, are rejected. Password whitespace is preserved. The removed
`POST /customers` endpoint can no longer create passwordless accounts.

### Configuration and migration

Install dependencies with `uv sync`. Set these variables in your local `.env`
or process environment, alongside the existing PostgreSQL settings:

```dotenv
JWT_SECRET=<random-secret-at-least-32-characters>
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Generate a secret locally with `openssl rand -hex 32`; keep it private and stable
across API workers/restarts. There is no default signing secret. API startup
fails explicitly if the secret is missing or shorter than 32 characters.
If startup reports `JWT_SECRET must be configured with at least 32 characters`,
add the generated value as `JWT_SECRET` in the repository-root `.env` and restart
the app from the repository root (the `.env` path is relative to the working
directory). A process environment variable takes precedence over `.env`, so
remove or update any empty or short exported `JWT_SECRET` as well. Do not commit
the secret; the local `.env` is ignored by Git.
The expiry defaults to one day (1440 minutes) and must be a positive integer.
Tokens use HS256 with a fixed issuer and
audience and contain a user ID, not a trusted role. Every protected request
loads the current account, role and active status from PostgreSQL. Disabling an
account immediately invalidates its access; changing its role takes effect on
the next request. Rotating the signing secret invalidates existing tokens.

Apply the additive authentication migration:

```sh
uv run alembic upgrade head
uv run alembic current
```

Revision `c9e21a4b870d` follows `f4a19c6d2e83`. It adds nullable `password_hash`,
`role` (default `customer`, constrained to `customer`/`admin`), and `is_active`
(default true), preserving customer/cart data. Seeded customers remain
passwordless and cannot log in. There is deliberately no password-setting or
account-claiming endpoint for those accounts. Downgrading to `f4a19c6d2e83` drops
authentication fields and credentials, so do not downgrade a deployed system
without a backup.

### Admin bootstrap

Use trusted local/server CLI access and the intended database environment:

```sh
uv run python -m shopmind_api.bootstrap_admin \
  --name "Initial Admin" --email "admin@example.com"
```

The CLI prompts for and confirms the password without echoing it or accepting
it as a command-line argument. It creates a new admin account and refuses any
existing email, including seeded customers; it never promotes existing accounts.
Public registration always creates customers. No admin is seeded automatically.

### API permissions

| API | Access |
| --- | --- |
| `POST /auth/register`, `POST /auth/login` | Public |
| `GET /auth/me` | Any active authenticated account |
| `GET /products`, `GET /products/{product_id}` | Public |
| `GET /inventory/{product_id}` | Public |
| `PUT /inventory/{product_id}` | Admin only |
| All `/cart/{customer_id}` operations | Customer only, own ID |
| `POST /checkout/{customer_id}` | Customer only, own ID |
| `POST /orders/{order_id}/payments` | Customer only, own order |
| `GET /customers/{customer_id}` | Own profile or admin |
| `GET /customers/{customer_id}/orders` | Own history or admin |
| `GET /orders` | Customer's own orders; admin sees all (paginated) |
| `GET /orders/{order_id}`, `GET /orders/{order_id}/payments` | Own order or admin |
| `POST /customers` | Removed |
| `GET /health` | Public |

There are currently no category routes or product/category creation/modification
routes in this repository. Catalog browsing remains unchanged; future catalog
mutation endpoints must use `require_admin`. Reusable `get_current_user`,
`require_customer`, `require_admin` and ownership dependencies live in
`shopmind_api/dependencies/auth.py`. Missing, invalid, expired or inactive-account
tokens return 401 with `WWW-Authenticate: Bearer`; valid users with insufficient
permissions or another customer's ID/order receive 403.

### Logging

Central configuration lives in `shopmind_api/core/logging.py`. Application events
and sanitized exception traces go to `logs/shopmind.log`; account creation,
login success/failure, authentication/authorization denials, inventory updates,
order creation and payment outcomes go to `logs/audit.log`. Each file rotates at
5 MiB with five backups. The entire directory is Git-ignored. Bootstrap events
outside an HTTP request have correlation ID `-`.

HTTP responses include `X-Request-ID`. A valid UUID supplied in that header is
reused; otherwise a fresh UUID is generated. Request events log the route
template, method and status, never raw URLs/query strings, headers or bodies.
Passwords, hashes, JWTs, card numbers and CVV are never logged. Exception traces
omit exception messages and source/local values, because database/validation
exceptions can include secrets. SQL parameter echo and Uvicorn access logging
are suppressed. Sensitive auth/payment validation responses redact input values.
API debug traceback responses are disabled regardless of the existing `DEBUG`
setting. Failed request transactions roll back through the shared DB dependency.

### Troubleshooting `/auth/me` returning 401

For direct HTTP requests, the `Authorization` header must include the scheme
and a space before the token:

```http
Authorization: Bearer <access_token>
```

Sending only the token is rejected before JWT validation and logs
`authentication_failed reason=missing_token`. In Postman's **Authorization**
tab, select **Bearer Token** and paste only the token; Postman adds the prefix.
If setting the header manually, include `Bearer ` yourself.

Authentication denials are written to `logs/audit.log`, not the Uvicorn console.
The matching method, route and response status are in `logs/shopmind.log`.
The log directory is anchored to the repository root, regardless of the process
working directory. From the repository root, watch both files with:

```sh
tail -f logs/audit.log logs/shopmind.log
```

Match the response's `X-Request-ID` to `request_id` in both logs. If a correctly
formatted header still returns 401, check for `reason=invalid_token` (including
expired tokens or a changed signing secret) or
`reason=missing_or_inactive_account`. Obtain a fresh token through `/auth/login`.
Do not paste real tokens into logs or share them.

### Swagger/manual verification

Start the API with the configured environment:

```sh
uv run uvicorn shopmind_api.main:app --reload
```

Open `/docs`:

1. Register a customer, then call `POST /auth/login` with email/password.
   Copy `access_token`, click **Authorize**, and paste the token into the HTTP
   Bearer field (without adding a second `Bearer` prefix).
2. Call `/auth/me`; verify profile, role and active status, with no hash/password.
   Try a duplicate email (409), a registration `role` field (422), wrong
   credentials (401), and a seeded passwordless customer (401).
3. Verify public products/inventory reads work without a token. Inventory writes
   should return 401 anonymously, 403 as a customer, and succeed with a CLI-created
   admin token. Admins must receive 403 for cart/checkout/payment actions.
4. Register a second customer. Try that customer's cart, profile, checkout,
   history, order detail and payment URLs with the first customer's token (403).
   `/orders` must only return the first customer's orders; an admin sees all.
5. As a customer, add available stock to your cart and check out. Pay with the
   synthetic success/decline cards documented above; verify stock/cart behavior
   is unchanged and both outcomes appear in the audit log without payment data.
6. Check response `X-Request-ID` against application/audit events; invalid and
   expired tokens must return 401. Disable an account or change a role through
   trusted database access and confirm an already-issued token uses the new state.

Focused automated checks:

```sh
uv run pytest tests/unit/test_auth.py tests/unit/test_inventory.py \
  tests/unit/test_checkout_orders.py -q
```

No refresh tokens, OAuth, public role management or permission framework are
included. Use HTTPS for real deployments; the payment gateway remains a mock.

### Authentication change inventory

- New authentication implementation:
  [route](shopmind_api/api/routes/auth.py),
  [schemas](shopmind_api/schemas/auth.py),
  [service](shopmind_api/services/auth_service.py),
  [dependencies](shopmind_api/dependencies/auth.py),
  [password/JWT helpers](shopmind_api/core/security.py), and
  [admin CLI](shopmind_api/bootstrap_admin.py).
- Customer persistence:
  [migration](alembic/versions/c9e21a4b870d_add_customer_authentication.py),
  [model](shopmind_api/models/customer.py),
  [response schema](shopmind_api/schemas/customer.py),
  [repository](shopmind_api/repositories/customer_repository.py), and
  [service](shopmind_api/services/customer_service.py).
- Protected commerce routes:
  [cart](shopmind_api/api/routes/cart.py),
  [checkout](shopmind_api/api/routes/checkout.py),
  [customers](shopmind_api/api/routes/customers.py),
  [inventory](shopmind_api/api/routes/inventory.py), and
  [orders](shopmind_api/api/routes/orders.py).
  Order pagination/auditing and fresh locked state also update the
  [order service](shopmind_api/services/order_service.py) and
  [order repository](shopmind_api/repositories/order_repository.py).
- Logging/configuration/wiring:
  [central logging](shopmind_api/core/logging.py),
  [settings](shopmind_api/core/config.py),
  [database engine](shopmind_api/core/database.py),
  [database dependency](shopmind_api/dependencies/database.py),
  [application](shopmind_api/main.py), [.gitignore](.gitignore),
  [dependencies](pyproject.toml), and [lockfile](uv.lock).
- Focused verification:
  [auth tests](tests/unit/test_auth.py),
  [test configuration](tests/conftest.py), and authenticated fixtures in
  [inventory tests](tests/unit/test_inventory.py) and
  [checkout tests](tests/unit/test_checkout_orders.py).
  This README documents setup, permissions and manual checks.
