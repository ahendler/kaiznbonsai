# KaiznBonsai

KaiznBonsai is an inventory management web application tailored for Food & Beverage CPG (Consumer Packaged Goods) brands.

Deployed at Cloudfront URL: https://d1zfq2u3duxnio.cloudfront.net

## Repository Structure

- `backend/`: Django REST Framework API, containing the data models and CQRS business logic.
- `frontend/`: React + TypeScript user interface built with Vite.
- `infrastructure/`: AWS CDK code for defining the cloud deployment architecture.
- `docs/`: Technical planning, architecture documentation, and challenge details.
- `.github/workflows/`: CI/CD pipelines for automated build and deployment.

## Architecture Notes

This implementation fulfills (part of) the challenge requirements while incorporating specific design decisions:

- **CQRS Lite:** The backend order management module separates read models (selectors) from write operations (commands). This encapsulates business logic away from HTTP views and simplifies unit testing.
- **Data Isolation:** All database queries are scoped to the authenticated user's account using viewset querysets, DRF permissions, and ownership validation in serializers and commands, ensuring tenant data separation.
- **Infrastructure:** AWS CDK is utilized to define and deploy the cloud infrastructure.

## API Overview

- `POST /api/v1/auth/register/`, `POST /api/v1/auth/login/`, `POST /api/v1/auth/logout/`
- `GET /api/v1/auth/me/`
- `GET|POST|PATCH|DELETE /api/v1/inventory/products/`
- `GET|POST|PATCH|DELETE /api/v1/inventory/stocks/`
- `GET /api/v1/inventory/financials/`
- `GET /api/v1/inventory/financials/products/`
- `GET|POST|PATCH|DELETE /api/v1/orders/purchase-orders/`
- `POST /api/v1/orders/purchase-orders/{id}/confirm/`
- `POST /api/v1/orders/purchase-orders/{id}/cancel/`
- `GET|POST|PATCH|DELETE /api/v1/orders/sales-orders/`
- `POST /api/v1/orders/sales-orders/{id}/confirm/`
- `POST /api/v1/orders/sales-orders/{id}/cancel/`

## Local Development

1. Ensure Docker and `docker-compose` are installed.
2. Run `docker-compose up --build` in the root directory.
3. Access the frontend at `http://localhost:3000` and the backend at `http://localhost:8000`.

## Environment Variables

- `SECRET_KEY`
- `DEBUG`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `CORS_ALLOWED_ORIGINS`
- `VITE_API_URL`

_Refer to the `docs/` folder for detailed technical plans, API documentation, and architecture diagrams._
