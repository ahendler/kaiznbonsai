# Architectural Decisions and Considerations

This document tracks the technical and architectural choices made throughout the development of the kaiznbonsai inventory management application.

## Infrastructure & Database Deployment

Usually one would separate database and backend into different infrastructure, e.g. using Docker for backend and a managed DB service like AWS RDS or Supabase. For this challenge, Docker Compose orchestrates the entire application (Postgres, Django, React) to keep the local setup self-contained.

---

## Email as Login Credential

`User.USERNAME_FIELD = "email"`. Business-facing SaaS products authenticate with email, not an arbitrary username — users don't think in usernames. `username` is retained as a field because `AbstractUser` requires it internally (e.g. `createsuperuser`), but it is auto-set to equal the email on registration and is never exposed through the API.

---

## App Namespace: `apps/`

All Django apps live under `backend/apps/` (e.g. `apps.accounts`, `apps.inventory`, `apps.orders`). This prevents namespace collisions with third-party packages and makes it immediately clear what is project code vs. installed library. The `AppConfig.name` uses the full dotted path (`apps.accounts`), while the Django `app_label` remains the short name (`accounts`) for migrations.

---

## API Versioning: `/api/v1/`

All API routes are prefixed with `/api/v1/`. Established upfront to avoid breaking the frontend or external integrations when a v2 surface is needed. Zero additional cost if versioning is never needed; significant cost if routes need renaming after the frontend is integrated.

---

## CQRS Lite Pattern

Business logic is separated using a Command Query Responsibility Segregation (CQRS) Lite pattern. State-mutating logic (order confirmation, cancellation, stock adjustment) lives in `apps/<domain>/commands.py` as plain Python functions. Complex data retrieval lives in `apps/<domain>/selectors.py`. This logic does not live in views or serializers. Views are thin orchestrators: authenticate, parse request data, call commands/selectors, serialize and return the response.

**Why:** Splitting reads and writes clarifies side-effects. These functions are callable from views, management commands, Celery tasks, and tests without any HTTP mocking. This makes the core business rules testable in isolation at high speed.

---

## Test Settings Split

`config/settings_test.py` overrides `DATABASES` to SQLite in-memory so `pytest` runs locally without Docker. In CI and inside Docker Compose, tests use `config.settings` (full Postgres). This is set in `pytest.ini` via `DJANGO_SETTINGS_MODULE`.

---

## Planned: `CORS`, `drf-spectacular`, Logout (Phase 3)

- `django-cors-headers`: required before the React frontend can make cross-origin requests to the backend.
- `drf-spectacular`: generates OpenAPI schema + Swagger UI at `/api/schema/swagger-ui/` — required for API documentation criterion with zero per-endpoint overhead.
- Logout endpoint using `simplejwt` token blacklist: makes access tokens revocable. Without it, tokens are irrevocable until TTL expiry — a real security gap in multi-user systems.
