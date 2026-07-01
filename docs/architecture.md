# Architectural Decisions and Considerations

Technical and architectural choices for the KaiznBonsai inventory management application.

## Email as Login Credential

`User.USERNAME_FIELD = "email"`. Business-facing SaaS products authenticate with email, not an arbitrary username. `username` is retained because `AbstractUser` requires it internally (e.g. `createsuperuser`), but it is auto-set to equal the email on registration and is never exposed through the API.

## App Namespace: `apps/`

All Django apps live under `backend/apps/` (e.g. `apps.accounts`, `apps.inventory`, `apps.orders`). This prevents namespace collisions with third-party packages and makes it immediately clear what is project code vs. installed library. The `AppConfig.name` uses the full dotted path (`apps.accounts`), while the Django `app_label` remains the short name (`accounts`) for migrations.

## API Versioning: `/api/v1/`

All API routes are prefixed with `/api/v1/`. Established upfront to avoid breaking the frontend or external integrations when a v2 surface is needed.

## CQRS Lite Pattern

Business logic is separated using a Command Query Responsibility Segregation (CQRS) Lite pattern. State-mutating logic (order confirmation, cancellation, stock adjustment) lives in `apps/<domain>/commands.py` as plain Python functions. Complex data retrieval lives in `apps/<domain>/selectors.py`. Views are thin orchestrators: authenticate, parse request data, call commands/selectors, serialize and return the response.

**Why:** Splitting reads and writes clarifies side-effects. These functions are callable from views, management commands, and tests without HTTP mocking.

Write-side inventory mutations go through `apps/inventory/commands.py::record_movement()` — the single writer of `current_quantity` after batch creation.

## Stock Movement Ledger

`StockMovement` (`apps/inventory/models.py`) is an append-only ledger of quantity changes per batch. `Stock.current_quantity` is a **cache** updated only via `record_movement()`.

| Reason | Created by | Purpose |
|--------|------------|---------|
| `RECEIPT` | PO confirm, manual stock create | Opening quantity when a batch is introduced |
| `SALE` | `confirm_sales_order` | Stock deduction linked to a sales line (see Stock allocation below) |
| `RETURN` | `cancel_sales_order` | Reverses exact `SALE` rows on the original batches |
| `ADJUSTMENT` | `StockViewSet.perform_update` | Data-entry typo correction on unconsumed manual batches only |
| `VOID` | `void_manual_stock_batch` | Removes an unconsumed manual batch; sets `Stock.voided_at` |
| `RECEIPT_REVERSAL` | `cancel_purchase_order` | Reverses untouched PO receipt; sets `Stock.voided_at` on linked batches |

Movement rows power COGS, financial period aggregates, and the **Stock History** UI. They are exposed read-only via:

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/inventory/movements/` | Tenant-wide ledger; cursor-paginated; filterable by `reason`, `product`, `stock_batch`, `from`/`to`, `search` |
| `GET /api/v1/inventory/stocks/{id}/movements/` | Same serializer, scoped to one batch (stock drawer) |

Writes still go only through `record_movement()` in commands — never via these list endpoints.

### Batch creation

Every stock entry path follows the same pattern:

1. Create `Stock` with `initial_quantity = X`, `current_quantity = 0`
2. `record_movement(delta=+X, reason=RECEIPT)`

PO confirm and manual create both use this pattern. Never set `current_quantity` to the receipt amount on create and then call `record_movement(+X)` — that double-counts.

### Invariants

1. Every batch has one opening `RECEIPT` movement equal to `initial_quantity`.
2. `current_quantity == sum(movements.delta)` for that batch.
3. `SALE` movements are only created by `confirm_sales_order`.
4. `RETURN` movements are only created by `cancel_sales_order`, reversing exact `SALE` rows.
5. `VOID` movements are only created by `void_manual_stock_batch` on unconsumed, non-PO batches.
6. `RECEIPT_REVERSAL` movements are only created by `cancel_purchase_order` on untouched PO-linked batches.
7. `initial_quantity` is immutable after create, except typo correction on unconsumed manual batches (`ADJUSTMENT` bumps `initial_quantity` in lockstep).
8. COGS is derived from `SALE` movements on `CONFIRMED` sales orders only.
9. `record_movement` is the only code path that changes `current_quantity` after batch creation.
10. `ADJUSTMENT` is only for unconsumed, non-PO manual batches (serializer eligibility unchanged).
11. Voided batches (`voided_at` set) have `current_quantity = 0` and are hidden from the stock drawer by default; movement rows are never deleted.

### COGS and financials

COGS is the sum of `-delta × stock_batch.unit_cost` over `StockMovement` rows where `reason=SALE` and the linked sales order is `CONFIRMED`.

Revenue is the sum of `-delta × sales_order_item.unit_price` on those same `SALE` movements (movement-based so multi-batch confirms and period filters stay aligned). Inventory value is `Sum(current_quantity × unit_cost)` on `Stock` — always a **current snapshot**, not period-scoped.

When a sales order is cancelled, its `SALE` movements stay in the database for audit but are excluded from COGS by filtering on order status. `RETURN` movements restore stock but are not netted into the COGS calculation — cancelled orders simply drop out of the revenue and COGS aggregates.

**Qty purchased / qty sold (dashboard):** net movement deltas in the period — `RECEIPT` + `VOID` + `RECEIPT_REVERSAL` for purchases; `SALE` + `RETURN` for sales. Manual voids and order cancellations within the window net to zero without removing ledger rows.

**Per-product percentages** (dashboard product table; API field `margin`):

| Metric | Formula | API field | Notes |
|--------|---------|-----------|-------|
| Gross margin | `(profit ÷ revenue) × 100` | `margin` | `0` when revenue is 0 |
| Markup on cost | `(profit ÷ COGS) × 100` | `markup_on_cost` | `null` when COGS is 0 |

Gross margin is share of revenue kept after COGS. Markup on cost is profit relative to cost — e.g. 150% markup means profit is 1.5× COGS. Margin-band filters and sort-by-`-margin` use gross margin only.

**Period filtering (dashboard):** `GET /inventory/financials/` and `GET /inventory/financials/products/` accept optional inclusive `from` / `to` query params (`YYYY-MM-DD`). When both are omitted, aggregates are all-time. When set, revenue and COGS are scoped to confirmed `SALE` movements in the window; per-product qty purchased and qty sold net `RECEIPT`/`RECEIPT_REVERSAL` and `SALE`/`RETURN` respectively. Inventory value is unchanged (current snapshot).

Implemented in `apps/inventory/selectors.py` and `apps/inventory/financial_period.py`.

### Stock allocation on sales order confirm

When a draft sales order is confirmed, `confirm_sales_order` deducts stock batch-by-batch via `record_movement(SALE)`. The batch order is chosen per confirm request:

| `allocation_strategy` | Ordering | UI label (confirm modal) |
|-----------------------|----------|---------------------------|
| `FIFO` (default) | `created_at` ascending | Oldest stock first |
| `FEFO` | `best_before` ascending, nulls last; then `created_at` | Expiring soonest |

Passed in the body of `POST /api/v1/orders/sales-orders/{id}/confirm/` as `allocation_strategy`. Not stored on the order — each confirm is an explicit choice. Implementation: `apps/orders/allocation.py::available_batches_for_allocation()`.

**Hybrid FEFO null policy:** Batches without `best_before` are consumed after all dated batches. If every batch lacks a date, FEFO matches FIFO. Expiry is optional on PO lines and manual stock entry.

### `django-simple-history` on `Stock`

`Stock` carries `HistoricalRecords()`. Quantity changes from `record_movement` use `save_without_historical_record()` so batch history is not duplicated at movement frequency. The movement ledger is the audit trail for quantity; `HistoricalStock` covers other field changes on the batch model.

### Delete and cancel guards

**Stock batch void:** `DELETE /inventory/stocks/{id}/` returns 405 — batches are never deleted. Manual batches are removed via `POST /inventory/stocks/{id}/void/`, which appends a `VOID` movement and sets `voided_at`. Blocked when the batch is PO-linked (cancel the PO instead), already voided, has no remaining quantity, or has any `SALE` history. PO-linked batches cannot be voided from the drawer.

**Stock.voided_at:** nullable timestamp set when a batch is voided (manual or PO cancel). `voided_at IS NULL` = active for listing; voided batches are excluded from `GET /inventory/stocks/` unless `?include_voided=true`. Depleted batches (`current_quantity = 0` from sales) remain visible unless voided.

**Order delete:** `DELETE` on purchase or sales orders returns 409 when the order has any linked `StockMovement` rows (confirmed or cancelled). Draft orders with no movements may still be deleted. Cancel first to append compensating movements and preserve ledger integrity.

**PO cancel after a cancelled sale:** if stock from a PO was sold and the sale later cancelled, quantity is restored via `RETURN` but `SALE` rows remain. PO cancel is blocked in that case even when on-hand quantity matches the original receipt. **Trade-off:** audit history over PO reversal; unwinding a PO after commercial activity on its batches is not supported.

**PO cancel (untouched receipt):** appends `RECEIPT_REVERSAL` per linked batch and sets `voided_at` — the original `RECEIPT` row and `Stock` row are kept for audit.

### Inventory adjustments

Typo correction on unconsumed, manually created batches is supported via `ADJUSTMENT` movements in `StockViewSet.perform_update` (eligibility enforced in the serializer: not PO-linked, not partially consumed).

Shrinkage, spoilage, and count corrections on partially consumed batches are not implemented — those would require negative adjustments against batches where `current < initial` without breaking the movement invariants.

## Authentication: Cookie-Only Refresh

JWT access tokens are returned in the JSON body. Refresh tokens are **httpOnly cookies only** — no refresh token in the response body, no `sessionStorage` fallback on the frontend. `RefreshView` reads the cookie exclusively.

## CORS and API Documentation

- **`django-cors-headers`:** configured in `config/settings.py`. `CORS_ALLOWED_ORIGINS` is read from the environment and defaults to `http://localhost:3000`. In production the frontend and API share the same CloudFront origin, so CORS is only active in local development.
- **`drf-spectacular`:** generates OpenAPI 3 schema and interactive docs:
  - Swagger UI: `/api/docs/`
  - ReDoc: `/api/redoc/`
  - Raw schema: `/api/schema/`

## AI Chat Assistant

Natural-language Q&A on the dashboard, backed by Claude Sonnet 4.6 with adaptive thinking and tool use. The backend is stateless — the frontend sends the full in-session conversation on each turn.

| Endpoint | Purpose |
|----------|---------|
| `POST /api/v1/assistant/chat/` | Send `messages` (user/assistant turns); returns `{ "reply": "..." }` |

**Request body:** `{ "messages": [{ "role": "user" \| "assistant", "content": "..." }, ...] }` — include the new user message in the array before sending.

**Auth:** `IsAuthenticated` only. Tenant isolation is structural: every tool calls the existing selector layer with `user=request.user`.

**Agentic loop:** `ChatView` calls the Anthropic API with six read-only tool definitions (`get_overall_financials`, `get_products_with_financials`, `get_stock_levels`, `list_purchase_orders`, `list_sales_orders`, `list_stock_movements`). The model may iterate up to 10 tool rounds per request. Tool executors live in `apps/assistant/tools.py` and delegate to `apps/inventory/selectors.py` and `apps/orders/selectors.py`.

**Configuration:** `ANTHROPIC_API_KEY` (server-side only). Missing key does not crash startup; the chat endpoint returns 503 at call time.

**Frontend:** `AssistantFab` in `AppLayout` — FAB + `AIChatDrawer` on **Home** (`/`) and **Financials** (`/financials`). Chat history is lifted to layout state so it persists when switching between those pages. Not persisted across reloads. Cap at 20 messages sent to the backend per turn.

Implemented in `apps/assistant/`. See [`docs/phases/phase-31-ai-chat-assistant.md`](phases/phase-31-ai-chat-assistant.md).

## Frontend application shell

Authenticated routes live under `AppLayout` (burger-drawer nav). No backend routes — client-side React Router only.

| Path | Page | Purpose |
|------|------|---------|
| `/` | `HomePage` | Period KPI snapshot, needs-attention cards, recent stock movements |
| `/financials` | `FinancialsPage` | Period-scoped P&L summary + paginated product performance table |
| `/inventory/products` | `ProductListPage` | Product catalog; `?stock=out_of_stock` pre-filters stock level |
| `/orders/purchases` | `PurchaseOrdersPage` | Purchase order list; `?orderId=` opens detail modal |
| `/orders/sales` | `SalesOrdersPage` | Sales order list; `?orderId=` opens detail modal |
| `/history` | `HistoryPage` | Stock movement audit trail |

`/orders` redirects to `/orders/purchases`. Order deep links are built via `buildOrderPath()` in `frontend/src/utils/orders.ts` (used by History, batch activity, and Home widgets).

Nav: Home, Financials, Products, Purchases, Sales, Stock History. See [`docs/phases/phase-34-home-and-nav.md`](phases/phase-34-home-and-nav.md).

## Test Database: Always Postgres

Tests run against the Dockerized Postgres instance. `pytest.ini` points at `config.settings`, and the Postgres container must be running before executing the test suite:

```bash
docker compose up -d && docker compose exec backend pytest
```

**Why:** Production-parity testing removes environment-specific bugs. `pytest-django` creates a throwaway database per session — no shared state between runs.

## AWS Deployment (summary)

Production runs on AWS, defined in `infrastructure/` via CDK:

- **Frontend + API:** a single CloudFront distribution serves both. Static assets come from S3; `/api/*` and `/admin/*` paths route to Elastic Beanstalk. Frontend and API share the same origin — no CORS in production.
- **Backend:** ECR image on Elastic Beanstalk (Docker multicontainer: Django + Postgres on one EC2 instance)
- **CI/CD:** GitHub Actions builds and deploys on push to `main`

Production Elastic Beanstalk environment variables are set at CDK deploy time from `infrastructure/.env` (see [`infrastructure/README.md`](../infrastructure/README.md)).

---

## Known Compromises

### Infrastructure & Database Deployment

A standard production SaaS separates the backend from the database using a managed service like AWS RDS. To prioritize speed and minimize cost, both the Django application and PostgreSQL run as containers on a single Elastic Beanstalk instance (`backend/docker-compose.yml`). See the infrastructure README for the full topology and trade-offs.

### No multi-tenancy

The data model has no `Organization` entity. All user data is isolated at the row level via `queryset.filter(user=request.user)` — each user sees only their own inventory, orders, and financials. A production multi-tenant SaaS would introduce an `Organization` model with owner and member roles.

### Business logic trade-offs

- **PO-linked batches** cannot be voided from the drawer or have quantity/cost edited manually — cancel the PO to reverse an untouched receipt via `RECEIPT_REVERSAL`. Unconsumed manual batches support typo correction through `ADJUSTMENT` movements or full removal through `VOID`. Shrinkage on consumed batches is not supported yet.
- **Sales order cancellation** reverses each `SALE` with a matching `RETURN` on the same batch; `initial_quantity` is never modified.
- **PO cancellation** on untouched receipts voids linked batches via `RECEIPT_REVERSAL`; it is blocked once any batch from that PO has `SALE` history, even if a subsequent sale was cancelled and quantity was restored.
- **Partial fulfillments** are not supported — order confirmation is all-or-nothing.
