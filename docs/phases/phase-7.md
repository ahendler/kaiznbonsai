# Phase 7: Order Management UI

## Objective
To build the user interface for managing the complete lifecycle of Purchase Orders (inbound inventory) and Sales Orders (outbound inventory).

## Key Features
1. **Unified Orders Dashboard:** A single page utilizing tabs to cleanly separate Purchase Orders and Sales Orders without cluttering the main sidebar navigation.
2. **Order Lifecycle Actions:** Users can transition orders from `DRAFT` to `CONFIRMED` or `CANCELLED` via quick row actions.
3. **Dynamic Creation Drawers:** Slide-out drawers for creating orders that allow users to dynamically add multiple line items.
4. **Resilient Error Handling:** Backend validation errors (e.g., attempting to sell out-of-stock items, or attempting to cancel a PO whose stock has been consumed) are intercepted and displayed as clear, actionable toast notifications to the user.

## Architectural Decisions
- **Drawer vs. Modal:** Creating an order with multiple line items requires significant vertical space. Drawers were chosen over modals to provide a more comfortable and less claustrophobic UX.
- **Lazy Validation:** Instead of heavily calculating "cancellability" or stock availability proactively on the frontend, we rely on the strict, atomic backend constraints built in Phase 6. The UI acts as a thin client that safely catches HTTP 400 Bad Requests and explains the business rule violation to the user.
