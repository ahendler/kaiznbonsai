# Phase 1: Environment & Infrastructure Setup

## Objective

Establish the foundational architecture of the project. This involves creating the base directory structure, scaffolding both the Django backend and React frontend, and orchestrating them alongside a PostgreSQL database using Docker.

## Technical Specifications

### 1. Directory Structure

Create a clear separation of concerns at the root level:

- `/backend`: Python/Django application.
- `/frontend`: TypeScript/React application.
- `/docs`: Project documentation.
- `docker-compose.yml`: Root orchestration file.

### 2. Backend (Django)

- **Tooling:** Python (latest stable), pip (or Poetry/uv for dependency management).
- **Framework:** Django (latest stable), Django REST Framework.
- **Database:** `psycopg` (the modern standard PostgreSQL adapter for Python) to allow Django to communicate with Postgres.
- **Code Quality:** Configure `black` (formatting) and `flake8` (linting).
- **Setup:** Create a `requirements.txt` and initialize a standard Django project (`django-admin startproject config .`).

### 3. Frontend (React)

- **Tooling:** Node.js, npm/pnpm.
- **Framework:** React + TypeScript scaffolded via Vite.
- **Code Quality:** Configure ESLint and Prettier for strict typing and formatting.

### 4. Infrastructure (Docker)

- **`backend/Dockerfile`**: Python slim image, install requirements, run Gunicorn or Django dev server.
- **`frontend/Dockerfile`**: Node alpine image, install dependencies, run Vite dev server.
- **`docker-compose.yml`**:
  - `db`: PostgreSQL image (with volumes for persistence).
  - `backend`: Build from `./backend`, depends on `db`, exposes port `8000`.
  - `frontend`: Build from `./frontend`, exposes port `5173`. Volumes configured for hot-reloading.

## Acceptance Criteria

- [ ] Running `docker-compose up --build` successfully starts all three containers (db, backend, frontend) without crashing.
- [ ] The React welcome page is accessible at `http://localhost:5173` (or similar).
- [ ] The Django default landing page is accessible at `http://localhost:8000`.
- [ ] Making a change to a React component immediately triggers a Hot Module Replacement (HMR) update in the browser.
- [ ] Linters and formatters can be executed in both backend and frontend directories.
