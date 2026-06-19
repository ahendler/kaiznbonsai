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
- `PUT/PATCH /products/<id>/`: Update a product.
- `DELETE /products/<id>/`: Delete a product.

### Stock (Manual Adjustments)

- `GET /stocks/`: List all stock batches owned by the user.
- `POST /stocks/`: Manually create a new stock batch. Requires `product_id`, `initial_quantity` (which also sets `current_quantity`), and `unit_cost`.
- `PATCH /stocks/<id>/`: Manually adjust a batch (e.g., to reduce `current_quantity` due to spoilage).

## 3. Data Isolation & Security

- **Views:** Every ViewSet must override `get_queryset` to strictly filter by `user=request.user`.
- **Serializers:** The `user` field must be read-only. In `perform_create`, the view must inject `request.user` into the serializer's save method.
- **Validation:** When creating a `Stock` batch, the backend must verify that the `product_id` provided actually belongs to `request.user`.

## 4. Acceptance Criteria

- [ ] `TenantOwnedModel` is created in a shared location (e.g., an `apps/core/` app).
- [ ] `Product` and `Stock` models are created with appropriate fields and timestamps.
- [ ] Migrations are generated and run successfully.
- [ ] `ProductViewSet` handles CRUD operations and includes a dynamically calculated `total_stock` field on the read serializer.
- [ ] `StockViewSet` allows manual batch creation and `current_quantity` adjustments.
- [ ] Pytest suite proves that User A cannot see, modify, or add stock to User B's products.
- [ ] Pytest suite proves that the `sku` uniqueness constraint is enforced _per user_, allowing User A and User B to both have a product with SKU "123".
