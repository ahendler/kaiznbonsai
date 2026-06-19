# Phase 2: Backend Authentication API

## Objective

Configure the foundational database connection and establish a secure, production-grade authentication system on the backend. This phase covers Django settings hardening, a custom `User` model (email-first), and RESTful auth endpoints via DRF + `simplejwt`. The goal is a clean, fully tested auth layer that the frontend can integrate against in Phase 3.

---

## Technical Specifications

### 1. Security & Environment Configuration

- Extract the hardcoded `SECRET_KEY` and `DEBUG` values from `settings.py` into the `.env` file managed by `python-dotenv`.
- Configure `DATABASES` to connect to Postgres via `psycopg`, reading all credentials from the environment.

### 2. Custom User Model

Before running any initial migrations, define a custom `User` model inheriting from `AbstractUser`. This is non-negotiable: swapping the auth model after migrations exist is painful.

**Design decisions:**
- `email` is the primary login credential (`USERNAME_FIELD = "email"`).
- `username` is retained for `AbstractUser` compatibility (`createsuperuser`, Django admin) but is not surfaced through the API. It is auto-populated from the email local part on programmatic creation via `RegisterSerializer`.
- No roles or organization FK — data isolation is enforced at the queryset level (`filter(user=request.user)`), which is sufficient for the challenge scope.

Update `settings.py` with `AUTH_USER_MODEL = "accounts.User"`. Run migrations before any other app models are defined.

### 3. Authentication Endpoints (DRF & JWT)

Use `djangorestframework-simplejwt` for JWT issuance. Configure `DEFAULT_AUTHENTICATION_CLASSES` to `JWTAuthentication` and `DEFAULT_PERMISSION_CLASSES` to `IsAuthenticated` in `settings.py` so all endpoints are protected by default.

#### Endpoints

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| `POST` | `/api/v1/auth/register/` | Public | Creates a new user. Accepts `email` + `password` + `password_confirm`. |
| `POST` | `/api/v1/auth/login/` | Public | Authenticates and returns tokens + user payload (see below). |
| `POST` | `/api/v1/auth/token/refresh/` | Public | Exchanges refresh token for a new access token. |
| `POST` | `/api/v1/auth/logout/` | Authenticated | Blacklists the refresh token and clears the cookie. |
| `GET` | `/api/v1/auth/me/` | Authenticated | Returns the authenticated user's profile. |

#### Token Transport Strategy

The refresh token is stored in an **httpOnly cookie** — not returned in the JSON response body. This prevents XSS attacks from ever reading the refresh token via JavaScript. The access token is returned in the JSON body and held in memory by the frontend.

The login response body shape:

```json
{
  "access": "<short-lived JWT>",
  "user": { "id": 1, "email": "...", "first_name": "...", "last_name": "..." }
}
```

Embedding the user payload in the login response avoids an immediate `/me/` round-trip on app load.

The `RefreshView` reads the refresh token from the cookie first, falling back to the request body. This handles environments where cross-domain cookies are blocked (Safari ITP, privacy browsers).

The `LogoutView` blacklists the refresh token via `simplejwt`'s token blacklist and deletes the cookie. `INSTALLED_APPS` must include `rest_framework_simplejwt.token_blacklist`.

#### RegisterView

`AllowAny`. Accepts `email`, `password`, and `password_confirm`. `RegisterSerializer` validates password match and strength, auto-generates `username` from the email local part, and calls `User.objects.create_user()`.

#### MeView

Read: `GET` returns a `UserSerializer` with read-only fields. No write surface on this endpoint in this phase.

### 4. Test Layout

Tests live in `apps/accounts/tests/`. Split by concern:

- `test_registration.py` — covers: successful registration, duplicate email rejection, weak password rejection, mismatched passwords.
- `test_auth.py` — covers: successful login (returns access + user, refresh in cookie), wrong password returns 401, `/me/` without token returns 401, `/me/` with valid token returns user data, logout blacklists token.

Fixtures use plain `pytest` fixtures with `User.objects.create_user()` — no factory libraries.

---

## Acceptance Criteria

- [ ] `SECRET_KEY` is not present in any committed source file.
- [ ] Django connects to the Dockerized Postgres container successfully.
- [ ] `python manage.py migrate` runs clean with no warnings.
- [ ] `POST /api/v1/auth/register/` creates a user and returns `201`.
- [ ] `POST /api/v1/auth/login/` returns `{ access, user }` and sets an httpOnly refresh cookie.
- [ ] `GET /api/v1/auth/me/` without a token returns `401`.
- [ ] `GET /api/v1/auth/me/` with a valid token returns the user's profile.
- [ ] `POST /api/v1/auth/logout/` blacklists the token and clears the cookie.
- [ ] All `pytest` tests in `apps/accounts/tests/` pass.
