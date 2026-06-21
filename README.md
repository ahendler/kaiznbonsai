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
- **Data Isolation:** All database queries are scoped to the authenticated user's organization using custom querysets and middleware, ensuring strict tenant data separation.
- **Infrastructure:** AWS CDK is utilized to define and deploy the cloud infrastructure.

## Local Development

1. Ensure Docker and `docker-compose` are installed.
2. Run `docker-compose up --build` in the root directory.
3. Access the frontend at `http://localhost:3000` and the backend at `http://localhost:8000`.

_Refer to the `docs/` folder for detailed technical plans, API documentation, and architecture diagrams._
