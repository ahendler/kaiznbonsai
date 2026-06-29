# KaiznBonsai

Inventory management for Food & Beverage CPG brands — products, stock batches, purchase/sales orders, and financial reporting.

## Live

**https://d1zfq2u3duxnio.cloudfront.net**

API docs (Swagger): https://d1zfq2u3duxnio.cloudfront.net/api/docs/

## Quick start

```bash
cp .env.example .env          # set SECRET_KEY
docker compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |

## Tests

```bash
docker compose exec backend pytest
```

## Repository

| Path | Purpose |
|------|---------|
| `backend/` | Django REST API — models, CQRS commands/selectors, auth |
| `frontend/` | React + TypeScript UI (Vite, Mantine, TanStack Query) |
| `infrastructure/` | AWS CDK stacks and deploy runbook |
| `docs/` | [`architecture.md`](docs/architecture.md) — design decisions |
| `.github/workflows/` | CI/CD to AWS on push to `main` |

## Read more

- [`docs/architecture.md`](docs/architecture.md) — CQRS, data isolation, API docs, AWS summary
- [`infrastructure/README.md`](infrastructure/README.md) — CDK topology, `.env` config, CI/CD flow

## Stack

Django · DRF · PostgreSQL · React · TypeScript · Mantine · TanStack Query · AWS CDK · Elastic Beanstalk · CloudFront
