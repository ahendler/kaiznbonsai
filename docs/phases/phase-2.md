# Phase 2: Backend Authentication API

## Objective

Configure the foundational database connection and establish a secure authentication system on the backend. This phase focuses entirely on Django configuration, setting up a robust custom User model, and exposing RESTful endpoints for user registration, login, and session/token management via Django Rest Framework (DRF).

## Technical Specifications

### 1. Security & Environment Configuration

- Install `python-dotenv` to manage environment variables.
- Extract the hardcoded `SECRET_KEY` and `DEBUG` variables in `settings.py` and move them into a `.env` file.
- Configure Django's `DATABASES` setting to connect to PostgreSQL using the `psycopg` driver, reading the credentials (`POSTGRES_DB`, `POSTGRES_USER`, etc.) dynamically from the environment.

### 2. Custom User Model

- **Important:** Before running _any_ initial migrations, create a custom `User` model by inheriting from Django's `AbstractUser` (this is the official Django best practice for future-proofing).
- Update `settings.py` with `AUTH_USER_MODEL = 'your_app_name.User'`.
- Run `python manage.py makemigrations` and `python manage.py migrate` to build the foundational database tables inside the Postgres container.

### 3. Authentication Endpoints (DRF & JWT)

- Implement JSON Web Token (JWT) authentication using `djangorestframework-simplejwt`.
- Implement serializers and views for the following endpoints:
  - `POST /api/v1/auth/register/`: Accepts email + password, creates a new user.
  - `POST /api/v1/auth/token/` (Login): Authenticates and returns access + refresh tokens.
  - `POST /api/v1/auth/token/refresh/`: Exchanges a refresh token for a new access token.
  - `GET /api/v1/auth/me/`: Returns the currently authenticated user's details.
  - _Logout endpoint deferred to Phase 3 — requires `simplejwt` token blacklist, which is set up alongside frontend integration._
- Configure DRF's `DEFAULT_AUTHENTICATION_CLASSES` to use `JWTAuthentication` in `settings.py`.
- Configure DRF's `DEFAULT_PERMISSION_CLASSES` in `settings.py` to `IsAuthenticated`, ensuring all APIs are protected by default unless explicitly opened.

### 4. Testing

- Configure `pytest` and `pytest-django`.
- Write unit tests to verify:
  - Successful user registration.
  - Rejection of duplicate emails/usernames during registration.
  - Successful login returning a token.
  - Rejection of invalid login credentials.

## Acceptance Criteria

- [ ] `SECRET_KEY` is completely removed from source code and loaded via `.env`.
- [ ] Django successfully connects to the Dockerized PostgreSQL database.
- [ ] Running `python manage.py migrate` executes successfully and clears the "unapplied migrations" warning.
- [ ] A POST request to `/api/v1/auth/register/` creates a new user (email + password).
- [ ] A POST request to `/api/v1/auth/token/` with valid email + password returns access and refresh tokens.
- [ ] An unauthenticated GET request to `/api/v1/auth/me/` returns a `401 Unauthorized` status.
- [x] Running `pytest` passes all 6 authentication test cases.
