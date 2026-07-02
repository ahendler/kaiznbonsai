# Inventory & orders

Domain rules for products, stock batches, the movement ledger, and purchase/sales orders. Implementation: `backend/apps/inventory/` and `backend/apps/orders/`.

System overview: [Architecture](../architecture.md).

---

## Products

A **product** is a catalog entry: name, description, SKU, and unit of measure.

- SKU is unique **per user**, not globally.

### Catalog retention

A product can be deleted only while it has **no stock batch history**. Once any batch exists - including batches fully sold through - the product row is kept so movements, COGS, and lot traceability stay intact. This is for F&B audit requirements - the catalog reflects SKUs that have ever moved through inventory, not just SKUs currently on hand.

---

## Stock batches

Stock is tracked in **batches** (`Stock`), not as a single number per product. Each batch has:


| Field                 | Purpose                                                          |
| --------------------- | ---------------------------------------------------------------- |
| `id`                  | UUID — unique batch identifier                                   |
| `lot_code`            | Optional traceability label                                      |
| `best_before`         | Optional expiry date (used by FEFO allocation)                   |
| `initial_quantity`    | Quantity when the batch was introduced                           |
| `current_quantity`    | On-hand quantity (maintained by the ledger)                      |
| `unit_cost`           | Cost per unit for COGS                                           |
| `purchase_order_item` | Set when batch came from a confirmed PO; `null` for manual entry |
| `voided_at`           | Set when batch is voided; hidden from default listings           |


**Manual stock:** `POST /api/v1/inventory/stocks/` with `product`, `initial_quantity`, `unit_cost`, optional lot/expiry.

**PO stock:** created automatically when a purchase order is confirmed (see below).

**List batches:** `GET /api/v1/inventory/stocks/?product={id}`. Voided batches are excluded unless `?include_voided=true`.

### Batch retention

Stock batches are **never hard-deleted**. Each batch is a permanent cost-basis and traceability record; quantity changes append to the movement ledger instead of rewriting history. To remove a manual batch from available stock, use void (see below). PO-linked batches are reversed by cancelling the purchase order.

---



## Movement ledger

`StockMovement` is an **append-only** log of quantity changes. `Stock.current_quantity` is a cache updated only by `record_movement()` in `inventory/commands.py`.

### Movement reasons


| Reason             | Created by                                | Delta sign               | Purpose                                      |
| ------------------ | ----------------------------------------- | ------------------------ | -------------------------------------------- |
| `RECEIPT`          | Manual stock create, PO confirm           | Positive                 | Introduce quantity                           |
| `SALE`             | Sales order confirm                       | Negative                 | Deduct for sale                              |
| `RETURN`           | Sales order cancel                        | Positive                 | Reverse a prior `SALE`                       |
| `ADJUSTMENT`       | Stock batch PATCH (eligible batches only) | Either                   | Typo correction on unconsumed manual batches |
| `VOID`             | Manual void                               | Negative (remaining qty) | Remove unconsumed manual batch               |
| `RECEIPT_REVERSAL` | PO cancel (untouched receipt)             | Negative                 | Reverse PO receipt                           |


Movement rows are never deleted. They drive COGS, quantity aggregates, and the Stock History UI.

### Batch creation pattern

Every receipt path follows the same two steps:

1. Create `Stock` with `initial_quantity = X`, `current_quantity = 0`.
2. Call `record_movement(delta=+X, reason=RECEIPT)`.

Do not set `current_quantity` to the receipt amount on create and then call `record_movement(+X)` — that double-counts.

### Invariants

1. Every batch has an opening `RECEIPT` equal to `initial_quantity`.
2. `current_quantity == sum(movements.delta)` for that batch.
3. `SALE` rows are only created by `confirm_sales_order`.
4. `RETURN` rows reverse exact prior `SALE` rows on cancel.
5. `record_movement` is the only path that changes `current_quantity` after batch creation.
6. Voided batches have `current_quantity = 0` and `voided_at` set.



### Read endpoints


| Endpoint                                       | Scope                                                                                           |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `GET /api/v1/inventory/movements/`             | All movements for the user; filter by `reason`, `product`, `stock_batch`, `from`/`to`, `search` |
| `GET /api/v1/inventory/stocks/{id}/movements/` | Movements for one batch                                                                         |


Writes never go through these list endpoints.

---



## Manual batch edits and void



### Typo correction (`PATCH /api/v1/inventory/stocks/{id}/`)

Supported for **unconsumed, manually entered** batches — e.g. correcting 100 entered as 1000 before any sales. A quantity change appends an `ADJUSTMENT` movement and bumps `initial_quantity` by the same delta.

Requirements: batch not voided, not PO-linked, and not partially consumed (`current_quantity == initial_quantity`).

PO-linked batches: quantity and cost are fixed at receipt; `lot_code` and `best_before` can be updated and sync to the PO line.

### Void (`POST /api/v1/inventory/stocks/{id}/void/`)

Removes an **unconsumed manual batch** from available stock while keeping the batch and its movements for audit. Applies when the batch is manual (not PO-linked), has remaining quantity, and has never been used in a sale.

On success: `VOID` movement, `current_quantity → 0`, `voided_at` set.

---



## Purchase orders



### Lifecycle

```
DRAFT ──confirm──► CONFIRMED
  │                    │
  cancel               cancel (if allowed)
  ▼                    ▼
CANCELLED ◄──────── CANCELLED
```


| Action  | Endpoint                               | Effect                                                              |
| ------- | -------------------------------------- | ------------------------------------------------------------------- |
| List    | `GET /api/v1/orders/purchase-orders/`  | Paginated list; optional `?status=DRAFT\|CONFIRMED\|CANCELLED` (invalid → 400) |
| Create  | `POST /api/v1/orders/purchase-orders/` | `DRAFT` order + line items (`items_data`)                           |
| Confirm | `POST …/purchase-orders/{id}/confirm/` | `CONFIRMED`; one `Stock` batch + `RECEIPT` per line                 |
| Cancel  | `POST …/purchase-orders/{id}/cancel/`  | See rules below                                                     |
| Delete  | `DELETE …/purchase-orders/{id}/`       | Removes draft orders that have not yet affected stock; confirmed or cancelled orders with movement history are retained |


**Draft cancel:** status → `CANCELLED`; no stock impact.

**Confirmed cancel (untouched receipt):** for each linked batch with full on-hand quantity and no `SALE` history, appends `RECEIPT_REVERSAL`, sets `voided_at`. Once a batch from this PO has been used in a sale, the PO must stay confirmed — stock can be restored by cancelling the sale, but the purchase receipt remains part of the audit trail.

**Line item fields:** `product_id`, `quantity`, `unit_cost`, optional `lot_code`, optional `best_before`.

---



## Sales orders



### Lifecycle

Same status enum as purchase orders: `DRAFT` → `CONFIRMED` / `CANCELLED`.


| Action  | Endpoint                            | Effect                                                   |
| ------- | ----------------------------------- | -------------------------------------------------------- |
| List    | `GET /api/v1/orders/sales-orders/`  | Paginated list; optional `?status=DRAFT\|CONFIRMED\|CANCELLED` (invalid → 400) |
| Create  | `POST /api/v1/orders/sales-orders/` | `DRAFT` + lines (`product_id`, `quantity`, `unit_price`) |
| Confirm | `POST …/sales-orders/{id}/confirm/` | Deducts stock; see allocation below                      |
| Cancel  | `POST …/sales-orders/{id}/cancel/`  | Reverses `SALE` rows with matching `RETURN` if confirmed |
| Delete  | `DELETE …/sales-orders/{id}/`       | Same rules as PO delete                                  |


**Confirm requirements:**

- Order must be `DRAFT`.
- Each line must be fulfillable in full from available batches at confirm time.
- Batches are locked with `select_for_update()` during confirm.

**Confirm body (optional):**

```json
{ "allocation_strategy": "FIFO" }
```


| Strategy         | Batch order                                             |
| ---------------- | ------------------------------------------------------- |
| `FIFO` (default) | `created_at` ascending                                  |
| `FEFO`           | `best_before` ascending (nulls last), then `created_at` |


Strategy is chosen per confirm request; it is not stored on the order. Batches with `current_quantity > 0` are candidates (voided batches have zero quantity and are skipped).

**FEFO null policy:** batches without `best_before` are consumed after all dated batches. If every batch lacks a date, FEFO matches FIFO.

**Confirmed cancel:** for each `SALE` movement on the order, appends a `RETURN` with `delta = -sale.delta` on the same batch. Original `SALE` rows remain for audit; financial aggregates reflect order status (see [Financials](financials.md)).

---

## Draft orders

Draft purchase and sales orders are created in the UI or API with one or more line items. Order list pages support filtering by status via the API (`?status=`) and URL (`/orders/purchases?status=draft`, `/orders/sales?status=draft`). The `?orderId=` query param can be combined with `?status=` to open the detail modal on a filtered list. From draft you can:

- **Confirm** — apply stock effects (receipt for PO, deduction for SO).
- **Cancel** — mark cancelled; no stock change while still draft.
- **Delete** — remove the draft if it has not yet produced any stock movements.

To change line items on a draft, delete the draft and create a new one. Confirmed orders are adjusted through **cancel** (which writes compensating movements), not by editing lines in place.

---

## End-to-end flow (happy path)

1. **Register / login** — JWT access + refresh cookie.
2. **Create product** — e.g. SKU `TEA-001`, unit `KG`.
3. **Receive stock** — confirm a PO *or* POST manual stock with `unit_cost`.
4. **Create sales order** — draft with quantity and `unit_price`.
5. **Confirm sales order** — FIFO/FEFO deducts batches; `SALE` movements written.
6. **View financials** — revenue and COGS from confirmed `SALE` movements ([Financials](financials.md)).
7. **Stock History** — full movement audit trail in the UI.

---

## Code map


| Concern                   | Location                                                               |
| ------------------------- | ---------------------------------------------------------------------- |
| Movement writer           | `inventory/commands.py` → `record_movement`, `void_manual_stock_batch` |
| PO/SO commands            | `orders/commands.py`                                                   |
| Allocation                | `orders/allocation.py` → `available_batches_for_allocation`            |
| Serializers / eligibility | `inventory/serializers.py` → `StockSerializer.validate`                |
| Financial selectors       | `inventory/selectors.py`                                               |


