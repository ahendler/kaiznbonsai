# Financials

How revenue, cost, and margin metrics are defined and exposed. Implementation: `backend/apps/inventory/selectors.py`, `financial_period.py`, and `GET /api/v1/inventory/financials/`.

Domain context: [Inventory & orders](inventory-and-orders.md) (movements, confirm/cancel).

---

## API endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /api/v1/inventory/financials/` | Tenant-wide summary |
| `GET /api/v1/inventory/financials/products/` | Per-product table (cursor-paginated) |

Both accept optional **`from`** and **`to`** query params (`YYYY-MM-DD`, inclusive). Omit both for **all-time**. If one is set, both are required.

Swagger field types and filters: `/api/docs/`.

---

## Overall summary fields

Response from `GET /api/v1/inventory/financials/`:

| Field | Meaning |
|-------|---------|
| `revenue` | Sales income from confirmed orders |
| `cogs` | Cost of goods sold |
| `gross_profit` | `revenue − cogs` |
| `margin` | Gross margin % — `(gross_profit ÷ revenue) × 100`, or `0` when revenue is 0 |
| `inventory_value` | Current on-hand value — **not** filtered by period |

---

## Per-product fields

Response rows from `GET /api/v1/inventory/financials/products/`:

| Field | Meaning |
|-------|---------|
| `revenue`, `cogs`, `profit` | Same definitions as overall, scoped to product |
| `margin` | Gross margin % on that product |
| `markup_on_cost` | `(profit ÷ cogs) × 100`, or `null` when cogs is 0 |
| `qty_purchased` | Net units received in period (see below) |
| `qty_sold` | Net units sold in period (see below) |

### Product list filters

| Param | Values |
|-------|--------|
| `search` | Substring match on name or SKU |
| `margin_band` | `negative`, `low` (< 20%), `medium` (20–40%), `high` (≥ 40%) — uses gross margin |
| `activity` | `all`, `movement` (any qty in period), `stale` (no qty in period) |
| `ordering` | e.g. `-revenue`, `-profit`, `-margin`, `-markup_on_cost`, `-cogs`, `name`, `-created_at` |

---

## How revenue and COGS are calculated

Both use **`SALE` movements** where the linked sales order status is **`CONFIRMED`**.

Cancelled sales orders are excluded: their `SALE` rows remain in the database for audit but do not contribute to revenue or COGS.

```
revenue  = Σ ( −delta × sales_order_item.unit_price )   over qualifying SALE movements
cogs     = Σ ( −delta × stock_batch.unit_cost )         over the same movements
profit   = revenue − cogs
```

- `delta` is negative on `SALE` rows, so `-delta` is quantity sold.
- Multi-batch confirms (one line split across batches) are handled correctly because each movement carries its own batch cost and line price.

**Returns:** when a confirmed sale is cancelled, `RETURN` movements restore stock. Financial totals drop the order because status is no longer `CONFIRMED` — `RETURN` rows are not netted into the revenue/COGS sums.

---

## Quantity metrics

### `qty_sold` (per product, period-scoped)

Net sum of movement deltas where `reason` is `SALE` or `RETURN` and a sales order item is linked:

```
qty_sold = Σ (−delta)   over SALE and RETURN movements in the period
```

Cancellations within the period net out via `RETURN` rows.

### `qty_purchased` (per product, period-scoped)

Net sum of deltas where `reason` is `RECEIPT`, `RECEIPT_REVERSAL`, or `VOID`:

```
qty_purchased = Σ delta   over those movements in the period
```

Manual voids and PO cancels in the period reduce this total.

---

## Margin vs markup

| Term | Formula | API field | When revenue/cogs is zero |
|------|---------|-----------|---------------------------|
| **Gross margin** | `(profit ÷ revenue) × 100` | `margin` | `0` |
| **Markup on cost** | `(profit ÷ cogs) × 100` | `markup_on_cost` | `null` |

- **Gross margin** — share of revenue kept after COGS. Used for the overall badge and margin-band filters.
- **Markup on cost** — profit relative to cost. Shown as “Markup on Cost” in the product table.

---

## Worked example

Purchase 100 units at **$1**/unit ($100 total cost). Sell all 100 at **$10**/unit.

| Metric | Value |
|--------|-------|
| Revenue | $1,000 |
| COGS | $100 |
| Gross profit | $900 |
| Gross margin (`margin`) | **90%** |
| Markup on cost (`markup_on_cost`) | **900%** |


## Inventory value

```
inventory_value = Σ ( current_quantity × unit_cost )   over all Stock rows for the user
```

Includes batches with zero quantity (they contribute $0). Not scoped to a date range.

---

## UI mapping

| UI location | Data source |
|-------------|-------------|
| `/financials` — summary cards | `GET /inventory/financials/` |
| `/financials` — product table | `GET /inventory/financials/products/` |
| `/` — Home KPIs | Same overall endpoint with period filter |
| `/inventory/products` | Product catalog and on-hand totals; P&L per SKU on Financials |

---

## Code map

| Concern | Location |
|---------|----------|
| Overall + product aggregates | `selectors.py` → `get_overall_financials`, `get_products_with_financials` |
| Period parsing | `financial_period.py` → `parse_financial_period` |
| Query param validation | `financial_product_filters.py` |
| Views | `inventory/views.py` → `OverallFinancialsView`, `ProductFinancialsView` |

Tests: `backend/apps/inventory/tests/test_financials.py`.
