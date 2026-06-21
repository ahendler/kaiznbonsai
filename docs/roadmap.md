# Project Roadmap

## Phase 1: Environment & Infrastructure Setup

- Initialize Git repository and base directory structure.
- Scaffold Django (backend) and React + Vite (frontend) projects.
- Set up Docker and `docker-compose` to orchestrate Postgres, Django, and React containers.
- Configure linters, formatters, and environment variables.

## Phase 2: Backend Authentication API

- Configure Django project settings and PostgreSQL database connection.
- Set up custom User model.
- Implement authentication endpoints (Login, Logout, Registration) using DRF.
- Write tests for authentication endpoints and tenant isolation basics.

## Phase 3: Frontend Authentication UI

- Set up React application providers (Mantine UI, Tanstack Query).
- Implement Login and Registration UI screens.
- Create React context/hooks for auth state management.
- Implement protected routing to restrict access to authenticated users.

## Phase 4: Inventory Data Modeling & API

- Define Django models for `Product` and `Stock` (with unit types).
- Create database migrations.
- Develop REST API endpoints for Product CRUD operations.
- Develop REST API endpoints for manual Stock adjustments.
- Enforce user-level data isolation on all querysets.

## Phase 5: Inventory Management UI

- Build the Product listing page (data tables, pagination, filtering).
- Implement Product creation and editing modal/forms.
- Build the Stock management interface to visualize and manually adjust stock levels.
- Integrate Tanstack Query for data fetching and mutations.
- Implement stock deletion and validation edge cases in the UI (block deletion/initial qty edit if units are consumed).

## Phase 6: Order Management Data Modeling & API

- Define Django models for `PurchaseOrder` and `SalesOrder`.
- Create database migrations.
- Implement a **CQRS Lite** pattern separating business logic into `commands.py` (for mutations like confirm, cancel, stock adjustment) and `selectors.py` (for complex reads). Commands and selectors know nothing about HTTP. This keeps the logic testable in isolation.
- Develop REST API endpoints for creating and viewing orders (thin views, delegate to commands and selectors).
- Write command/selector unit tests covering: confirm increments stock, cancel of confirmed order reverses stock, insufficient stock raises error.

## Phase 7: Order Management UI

- Build the Purchase Orders listing and creation forms.
- Build the Sales Orders listing and creation forms.
- Ensure forms dynamically fetch and display available Products.

## Phase 8: Financial Logic & API

- Implement backend selectors/properties to calculate total purchase costs and sales revenue.
- Implement backend logic to calculate profit and profit margins per product and overall.
- Create specific API endpoints or augment existing ones to serve aggregated financial data.
- Write unit tests (`pytest`) for all financial calculations.

## Phase 9: Financial Dashboard UI

- Build the main landing dashboard for authenticated users.
- Implement metric cards showing overall Revenue, Costs, and Profit.
- Build visualizations (charts or tables) for individual product profit margins.
- Integrate backend financial APIs with the frontend UI.

## Phase 10: Final Polish, Testing & Deployment

- Conduct end-to-end testing of the entire flow.
- Apply UI/UX polish (responsive design checks, loading states, empty states).
- Finalize API documentation and the project README.
- Prepare the application for cloud deployment.

## Phase 11: AI Assistant (Post-Challenge Roadmap)

> Beyond the challenge requirements — demonstrates initiative and product thinking.

- Natural language query interface: users ask business questions in plain English (e.g. "What were my top 3 products last month?").
- Backend generates a safe, read-only SQL query via LLM, executes it against the org-scoped data, and returns a structured result plus a plain-English summary.
- Sandboxed: only SELECT queries, always filtered to `organization = request.user.organization`.
- Lives in `apps/assistant/` — isolated app, no coupling to core inventory logic.
