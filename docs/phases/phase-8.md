# Phase 8: Financial Logic & API

## Objective

Implement backend financial calculations to determine Revenue, Cost of Goods Sold (COGS), Gross Profit, and Profit Margins. This logic must be exposed via REST endpoints for consumption by the frontend dashboard.

## Technical Requirements

### 1. Financial Mathematics

To ensure accounting accuracy, Profit is calculated using **Cost of Goods Sold (COGS)** rather than simple cash flow (total spent).

The core formulas are:

- **Total Revenue**: `Sum(quantity * unit_price)` for all line items belonging to `CONFIRMED` Sales Orders.
- **COGS**: `Sum((initial_quantity - current_quantity) * unit_cost)` for all Stock batches.
- **Inventory Value on Hand**: `Sum(current_quantity * unit_cost)` for all Stock batches.
- **Gross Profit**: `Total Revenue - COGS`
- **Profit Margin**: `(Gross Profit / Total Revenue) * 100`

### 2. CQRS Selectors (`apps/inventory/selectors.py`)

Business logic is decoupled from HTTP views using the CQRS pattern.

- `get_overall_financials(user: User) -> dict`: Returns an aggregated dictionary of the user's total revenue, total COGS, total profit, and margin.
- `get_products_with_financials(user: User) -> QuerySet`: Uses Django's `.annotate()` to calculate revenue, COGS, and profit per product using database-level aggregation.

### 3. API Endpoints

- `GET /api/v1/inventory/financials/`: A new endpoint that returns the global financial metrics.
- `GET /api/v1/inventory/financials/products/`: A dedicated analytical endpoint returning a list of products annotated with `revenue`, `cogs`, `profit`, and `margin`.

### 4. Testing

Unit tests (`test_financials.py`) must be written to simulate:

1. Creating stock at varying price points.
2. Generating Sales Orders to consume partial stock.
3. Asserting that the Revenue, COGS, and Margin calculations follow the mathematical formulas defined above.
