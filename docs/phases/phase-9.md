# Phase 9: Financial Dashboard UI

## Objective
Build the primary analytics dashboard to visualize the financial data exposed by the backend in Phase 8. This dashboard will serve as the default landing page for authenticated users.

## Technical Requirements

### 1. API Integration
- Implement React Query hooks (`useOverallFinancials`, `useProductFinancials`) in a dedicated API module (`frontend/src/api/financials.ts`).
- Ensure proper query caching and loading states are handled globally.

### 2. Dashboard UI Architecture
- **Global Metrics Section**: Render a responsive grid of metric cards displaying:
  - Total Revenue
  - Total COGS
  - Gross Profit
  - Profit Margin
  - Total Inventory Value
- **Product Performance Section**: Render a data table displaying per-product financial metrics.
  - Include visual indicators (e.g., Progress bars) for the Profit Margin column to facilitate quick data scanning without requiring heavy external charting libraries.

### 3. Navigation & Routing
- Update the application router (`App.tsx`) to set the Dashboard as the index route (`/`) for authenticated users.
- Update the main application shell (`AppShell.tsx`) to include a navigation link to the Dashboard.

### 4. Synthetic Data Generation
- Create a Django management command (`generate_seed_data.py`) to populate the system with realistic data.
- **Requirement**: The script must NOT write directly to the `Stock` tables to fake data. It must instantiate `PurchaseOrder` and `SalesOrder` records and invoke the CQRS commands (`confirm_purchase_order`, `confirm_sales_order`) to execute the real business logic, ensuring a complete and valid audit history.

#### Synthetic Data Schema
The script will perform the following actions sequentially to simulate a real Food & Beverage CPG business lifecycle:

**1. Create User & Products**
- User: `demo@example.com` / `Password123!`
- Products:
  - Organic Espresso Beans (`COFF-01`, UoM: `KG`)
  - Oat Milk Barista Blend (`OAT-01`, UoM: `L`)
  - Ceremonial Matcha (`MAT-01`, UoM: `KG`)
  - Craft Kombucha - Ginger (`KMB-01`, UoM: `EA`)
  - Cold Brew Filter Bags (`BAG-01`, UoM: `EA`)

**2. Purchase Orders (Inbound)**
- **PO-001 (Initial Stockup) -> CONFIRMED:**
  - COFF-01: 1000 KG @ $12.00
  - OAT-01: 500 L @ $1.50
- **PO-002 (Tea & Supplies) -> CONFIRMED:**
  - MAT-01: 100 KG @ $40.00
  - BAG-01: 5000 EA @ $0.10
- **PO-003 (Kombucha Drop) -> CONFIRMED:**
  - KMB-01: 2000 EA @ $1.20
- **PO-004 (Restock Espresso at higher cost) -> CONFIRMED:**
  - COFF-01: 500 KG @ $14.00 (Tests FIFO cost deduction later)
- **PO-005 (Supplier Backout) -> CANCELLED:**
  - OAT-01: 1000 L @ $1.60 (Tests cancellation logic, no stock generated)
- **PO-006 (Alternative Oat Milk Restock) -> CONFIRMED:**
  - OAT-01: 500 L @ $1.60

**3. Sales Orders (Outbound)**
- **SO-001 (Local Cafe) -> CONFIRMED:**
  - COFF-01: 100 KG @ $25.00
  - OAT-01: 50 L @ $4.00
- **SO-002 (Retail Chain) -> CONFIRMED:**
  - KMB-01: 500 EA @ $3.50
  - MAT-01: 20 KG @ $90.00
- **SO-003 (Wholesale Deal Fell Through) -> CANCELLED:**
  - COFF-01: 200 KG @ $24.00 (Tests cancellation logic, stock must be refunded/not deducted)
- **SO-004 (Large Distributor) -> CONFIRMED:**
  - COFF-01: 950 KG @ $22.00 (Consumes remaining 900 from PO-001 @ $12.00 cost, and 50 from PO-004 @ $14.00 cost, proving FIFO logic works perfectly across batches).
- **SO-005 (Cafe Restock) -> CONFIRMED:**
  - BAG-01: 1000 EA @ $0.30
  - OAT-01: 100 L @ $4.00
- **SO-006 (Pending Negotiation) -> DRAFT:**
  - KMB-01: 100 EA @ $3.50 (Remains in DRAFT, no stock deducted)
