# Phase 4: Inventory Data Modeling & API

## Objective

Establish the foundational data models for the inventory system (`Product` and `Stock`) and expose them via a RESTful API. The architecture must support tenant isolation (users only see their own data) and enable financial tracking in future phases.

## Core Architectural Decision: The "Batch" Pattern

To calculate profit margins later, we must track the specific purchase cost of every unit sold.
Therefore, **Stock is not a simple integer counter on the Product model.** Instead, every addition of inventory (whether manual or via a purchase order) creates a distinct `Stock` record representing a **batch**.

When a product is sold in Phase 6, we will use FIFO (First-In, First-Out) logic to deplete the oldest stock batches first, locking in the exact profit margin based on that specific batch's `unit_cost`.

## 1. Data Models

We will create a new Django app called `inventory`.

### `core.models.TenantOwnedModel` (Abstract)

All domain models must inherit from this abstract base class. It ensures consistent auditing, enables chronological sorting (required for FIFO), and guarantees that every piece of data is strictly owned by a specific user for tenant isolation.

- `user`: `ForeignKey(settings.AUTH_USER_MODEL)` — Guarantees data isolation.
- `created_at`: `DateTimeField(auto_now_add=True)`
- `updated_at`: `DateTimeField(auto_now=True)`

### `inventory.models.Product`

The definition of an item available in the system. Inherits from `TenantOwnedModel`.
- `name`: `CharField`
- `description`: `TextField(blank=True)`
- `sku`: `CharField` — Must be unique **per user**, not globally.
- `unit_of_measure`: `CharField(choices=[('KG', 'Kilogram'), ('G', 'Gram'), ('L', 'Liter'), ('ML', 'Milliliter'), ('UNIT', 'Unit')])`

### `inventory.models.Stock`

A physical batch of inventory.

- `id`: `UUIDField(primary_key=True, default=uuid.uuid4)`
- `product`: `ForeignKey(Product, related_name='stock_batches')`
- `lot_code`: `CharField` — Human-readable batch identifier (e.g., "LOT-2026-A"). Satisfies the "unique identifier" requirement along with the ID.
- `best_before`: `DateField(null=True, blank=True)` — Critical for Food & Beverage CPG.
- `initial_quantity`: `DecimalField` — How much was originally added.
- `current_quantity`: `DecimalField` — How much is currently available. Drops to 0 when depleted.
- `unit_cost`: `DecimalField` — The purchase cost per unit of measure for this specific batch.

## 2. API Endpoints

All endpoints are nested under `/api/v1/inventory/`.

### Products

- `GET /products/`: List all products owned by the user. The serializer should use Django's `annotate` to include an aggregate `total_stock` field (sum of `current_quantity` of all related stock batches).
- `POST /products/`: Create a new product.
- `GET /products/<id>/`: Retrieve a product.
- `PUT/PATCH /products/<id>/`: Update a product. All changes are tracked via the audit log.
- `DELETE /products/<id>/`: Delete a product. **Blocked at the view layer** if any `Stock` batches reference it. Returns a `409 Conflict` with a descriptive error message. See Section 4 for rationale.

### Stock (Manual Adjustments)

- `GET /stocks/`: List all stock batches owned by the user.
- `POST /stocks/`: Manually create a new stock batch. Requires `product_id`, `initial_quantity` (which also sets `current_quantity`), and `unit_cost`.
- `PATCH /stocks/<id>/`: Manually adjust a batch (e.g., correct a data entry error). All changes are tracked via the audit log.
- `DELETE /stocks/<id>/`: Allowed in Phase 4 provided the batch has not been consumed by a sales order. The history log preserves the full record regardless of deletion. In Phase 6, a guard will be added to block deletion if `current_quantity < initial_quantity` (indicating units have been consumed by a confirmed sale).

## 3. Data Isolation & Security

- **Views:** Every ViewSet must override `get_queryset` to strictly filter by `user=request.user`.
- **Serializers:** The `user` field must be read-only. In `perform_create`, the view must inject `request.user` into the serializer's save method.
- **Validation:** When creating a `Stock` batch, the backend must verify that the `product_id` provided actually belongs to `request.user`.

## 4. Data Integrity, Mutation & Deletion Policy

### The Problem
Inventory data is financial data. Silent mutations or deletions destroy the audit trail required to:
- Reconstruct historical stock levels
- Verify FIFO cost-basis calculations
- Debug user errors (e.g., a quantity entered as 100 instead of 1000)

### Deletion Scenarios

| Operation | Policy | Reason |
|---|---|---|
| `DELETE /products/<id>/` with active stock batches | **Blocked (409 Conflict)** | Deleting a product with stock would silently destroy its batch records. The user must first remove or deplete all stock batches. |
| `DELETE /products/<id>/` with no stock | **Allowed** | Safe to proceed. |
| `DELETE /stocks/<id>/` not consumed by a sale | **Allowed** | A user may need to delete a batch entered in error. History preserves the record. |
| `DELETE /stocks/<id>/` partially or fully consumed by a sale | **Blocked in Phase 6** | Once a batch contributes to a confirmed sales order, deletion would corrupt the cost-basis for that sale's profit calculation. This guard is deferred to Phase 6 when the `SalesOrderItem` → `Stock` relationship exists. |

### Mutation Tracking: `django-simple-history`

All `Product` and `Stock` models will use `django-simple-history` to maintain a full, immutable audit log of every field change. This is added as a model-level field (`HistoricalRecords()`) and is transparent to the API consumer. It generates a parallel `_history` table in Postgres per model.

`django-simple-history` also supports point-in-time rollbacks. Any historical snapshot can be restored by calling `.save()` on the retrieved historical instance. This is the data infrastructure for a future "undo" endpoint, even if that endpoint is not built in this phase.

**Production note:** In a compliance-heavy environment, this would be complemented by `models.PROTECT` on the `ForeignKey` as a database-level safety net, in addition to the application-level guard in the ViewSet.

## 5. Acceptance Criteria

- [x] `TenantOwnedModel` is created in a shared location (e.g., an `apps/core/` app).
- [x] `Product` and `Stock` models are created with appropriate fields and timestamps.
- [x] `django-simple-history` is installed and `HistoricalRecords()` is present on both models.
- [x] Migrations are generated and run successfully.
- [x] `ProductViewSet` handles CRUD operations and includes a dynamically calculated `total_stock` field on the read serializer.
- [x] `DELETE /products/<id>/` returns `409 Conflict` when the product has active stock batches.
- [x] `StockViewSet` allows manual batch creation and `current_quantity` adjustments via `PATCH`.
- [x] Pytest suite proves that User A cannot see, modify, or add stock to User B's products.
- [x] Pytest suite proves that the `sku` uniqueness constraint is enforced _per user_, allowing User A and User B to both have a product with SKU "123".
- [x] Pytest suite covers the product deletion guard (product with active stock returns 409).
- [x] Pytest suite covers full stock CRUD operations including happy paths, ownership injection, and negative quantity validation.
