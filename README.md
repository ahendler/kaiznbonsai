# KaiznBonsai

Inventory management for Food & Beverage CPG brands — products, stock batches, purchase/sales orders, and financial reporting.

## Live

**https://d2m21gazqboxr5.cloudfront.net**


### Demo account (seeded via github workflow)

Email: `demo@example.com`

Password: Shared via email

---

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/api/docs/ |


Seed demo data locally:
```bash
docker compose exec backend python manage.py generate_seed_data
```
Email: `demo@example.com`
Password: `Password123!`

---

## Tests

```bash
docker compose exec backend pytest
```

Runs in CI on push/PR to `main` when backend files change (`.github/workflows/test.yml`).

---

## Documentation

| Doc | Description |
|-----|-------------|
| [Architecture](docs/architecture.md) | System design, data model, auth, API summary |
| [Inventory & orders](docs/domain/inventory-and-orders.md) | Stock ledger, PO/SO lifecycle, allocation |
| [Financials](docs/domain/financials.md) | Revenue, COGS, margins, period filters |
| [Infrastructure](infrastructure/README.md) | AWS CDK deploy and CI/CD |
| [API (Swagger)](https://d2m21gazqboxr5.cloudfront.net/api/docs/) | Interactive endpoint reference |

---

## Repository

| Path | Purpose |
|------|---------|
| `backend/` | Django REST API — commands/selectors, auth, tests |
| `frontend/` | React + TypeScript UI (Vite, Mantine, TanStack Query) |
| `infrastructure/` | AWS CDK stacks |
| `docs/` | Architecture and domain documentation |
| `.github/workflows/` | Test and deploy pipelines |

---

## Stack

Django · DRF · PostgreSQL · React · TypeScript · Mantine · Tailwind CSS · TanStack Query · AWS CDK · Elastic Beanstalk · CloudFront
