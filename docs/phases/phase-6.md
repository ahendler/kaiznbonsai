# Phase 6: Order Management Data Modeling & API

## Context
In Phase 5, we established the manual inventory system. However, real-world CPG operations move inventory through formalized transactions: Purchase Orders (buying goods) and Sales Orders (selling goods). 

Phase 6 focuses strictly on the **Backend Architecture** to support these transactions, setting the stage for the UI in Phase 7 and financial calculations in Phase 8.

## Objectives
1. Define the data models for `PurchaseOrder` and `SalesOrder`.
2. Implement a **CQRS Lite** architecture to separate complex business logic (stock allocation, FIFO deduction) from the HTTP layer.
3. Expose clean, thin REST endpoints to interact with the underlying commands and selectors.

---

## 1. Data Models (`apps/orders/models.py`)

We will create a new Django app `apps/orders` with the following models:

### Purchase Orders (Inbound)
*   **`PurchaseOrder`**:
    *   `user`: ForeignKey to the Auth User.
    *   `status`: CharField choices (`DRAFT`, `CONFIRMED`, `CANCELLED`). Default is `DRAFT`.
    *   `order_date`: DateField.
*   **`PurchaseOrderItem`**:
    *   `order`: ForeignKey to `PurchaseOrder`.
    *   `product`: ForeignKey to `Product`.
    *   `quantity`: DecimalField.
    *   `unit_cost`: DecimalField (the cost of goods).
    *   `lot_code`: CharField (optional).
    *   `best_before`: DateField (optional).

### Sales Orders (Outbound)
*   **`SalesOrder`**:
    *   `user`: ForeignKey.
    *   `status`: CharField choices (`DRAFT`, `CONFIRMED`, `CANCELLED`). Default is `DRAFT`.
    *   `order_date`: DateField.
*   **`SalesOrderItem`**:
    *   `order`: ForeignKey to `SalesOrder`.
    *   `product`: ForeignKey to `Product`.
    *   `quantity`: DecimalField.
    *   `unit_price`: DecimalField (the price sold to the customer).

---

## 2. CQRS Architecture

To ensure the backend is robust and testable without the complexity of DRF Serializer overrides, we will adopt a CQRS (Command Query Responsibility Segregation) Lite pattern.

*   **`selectors.py`**: Contains read-only query logic.
*   **`commands.py`**: Contains all mutation logic. Views and Serializers simply validate input and pass it to these commands.

### Core Commands (`apps/orders/commands.py`)

#### Purchase Order Commands
*   `create_purchase_order(user, data) -> PurchaseOrder`
*   `confirm_purchase_order(order) -> None`
    *   *Logic:* Iterates over `PurchaseOrderItem`s and creates new `Stock` batches with `initial_quantity = quantity`, `current_quantity = quantity`, and `unit_cost = unit_cost`. Transitions status to `CONFIRMED`.
*   `cancel_purchase_order(order) -> None`
    *   *Logic:* Finds the `Stock` batches created by this order and deletes them (or errors out if the stock has already been consumed by a sales order). Transitions status to `CANCELLED`.

#### Sales Order Commands
*   `create_sales_order(user, data) -> SalesOrder`
*   `confirm_sales_order(order) -> None`
    *   *Logic:* Iterates over `SalesOrderItem`s and implements **FIFO (First In, First Out)** stock deduction. It finds the oldest `Stock` batches for the product and decreases their `current_quantity`. If `total_stock < requested_quantity`, it rolls back the transaction and raises an `InsufficientStockException`. Transitions status to `CONFIRMED`.
*   `cancel_sales_order(order) -> None`
    *   *Logic:* Reverts the FIFO deduction, returning the deducted quantities back to the `current_quantity` of their respective `Stock` batches. Transitions status to `CANCELLED`.

---

## 3. REST API (`apps/orders/views.py`)

We will expose the following endpoints:

*   **`GET /api/v1/orders/purchase/`**: List user's POs.
*   **`POST /api/v1/orders/purchase/`**: Create a DRAFT PO.
*   **`POST /api/v1/orders/purchase/<id>/confirm/`**: Calls `confirm_purchase_order`.
*   **`POST /api/v1/orders/purchase/<id>/cancel/`**: Calls `cancel_purchase_order`.

*   **`GET /api/v1/orders/sales/`**: List user's SOs.
*   **`POST /api/v1/orders/sales/`**: Create a DRAFT SO.
*   **`POST /api/v1/orders/sales/<id>/confirm/`**: Calls `confirm_sales_order`.
*   **`POST /api/v1/orders/sales/<id>/cancel/`**: Calls `cancel_sales_order`.

---

## Acceptance Criteria
- [ ] Database schemas for `PurchaseOrder`, `PurchaseOrderItem`, `SalesOrder`, and `SalesOrderItem` are created and migrated.
- [ ] `commands.py` is implemented with rigorous atomic transactions for stock deduction.
- [ ] Pytest unit tests directly invoke `commands.py` to prove FIFO deduction and Insufficient Stock edge cases work perfectly without HTTP overhead.
- [ ] DRF endpoints are created and functional.
