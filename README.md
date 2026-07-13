# Squad Builder ⚽

A full-stack web app that lets users select their own England World Cup squad from real player data.

Users can browse players, filter by position and nationality, and build a 26-player squad — just like a national team manager.

Built with a modern Python backend, PostgreSQL database, and React frontend.

---

## Features

- Browse real football player data
- Filter by nationality, position, and name
- Select and manage a 26-player squad
- Persist squad locally in browser
- Refresh data from external API
- FastAPI backend with PostgreSQL storage
- Modern, reproducible development environment

---

## Tech Stack

### Backend

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL
- psycopg3
- uv (Python package manager)
- mise (runtime manager)

### Frontend

- React
- TypeScript
- Vite
- pnpm

### Infrastructure

- Docker
- Docker Compose
- Azure Bicep deployment for backend and frontend infrastructure
- Backend is deployed to App Service with Python 3.12 runtime; the local Dockerfile remains available for future container-based deployment

---

## Azure Deployment

The deployed application is live at:

- Frontend: `https://lively-wave-0ed7cbc10.7.azurestaticapps.net`
- Backend API: `https://squadbuilder-backend-ukwest.azurewebsites.net`
- Health endpoint: `https://squadbuilder-backend-ukwest.azurewebsites.net/api/health`

### Production architecture

- React/Vite frontend on Azure Static Web Apps
- FastAPI backend on Azure App Service
- PostgreSQL storage on Azure Database for PostgreSQL Flexible Server
- Application Insights for backend monitoring
- GitHub Actions for infrastructure provisioning and deployment

### Azure services used

- Azure Resource Group
- Azure App Service Plan (Linux) in UK West
- Azure App Service (backend) in UK West
- Azure Database for PostgreSQL Flexible Server in UK West
- Azure Static Web Apps in Central US
- Application Insights in UK West

> Static Web Apps is deployed in Central US because the preferred European regions were unavailable to this subscription at deployment time.

### Infrastructure-as-code

- `infra/main.bicep` defines backend App Service, Static Web App, App Insights, and runtime settings.
- `infra/main.parameters.json` contains placeholder deployment parameters.
- `.github/workflows/azure-deploy.yml` provisions Azure resources and deploys the frontend and backend.

### Deployment prerequisites

Required GitHub secrets for production deployment:

- `AZURE_CREDENTIALS`
- `AZURE_STATIC_WEB_APPS_API_TOKEN`
- `JWT_SECRET_KEY`
- `FOOTBALL_DATA_API_TOKEN`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`

### Deploy via GitHub Actions

- Pushes to `main` deploy infrastructure and both applications.
- Manual workflow runs can deploy infrastructure only, or deploy both apps when
  `deploy_apps=true`.
- The frontend build receives the backend URL from the infra job and sets
  `VITE_API_BASE` to `${BACKEND_URL}/api`.
- The backend deploy uses Azure login and `azure/webapps-deploy@v3` with
  `app-name`, so it does not require a publish profile.
- The deployment is safe to rerun without deleting production database data.

### Local deployment guidance

For development, continue using `make backend-dev` and `make frontend-dev`.

---

## Architecture Overview

```
React Frontend
      ↓
FastAPI Backend
      ↓
PostgreSQL Database
      ↓
football-data.org API
```

---

## Requirements

Install dependencies:

```bash
brew install mise uv pnpm docker
```

Install runtimes:

```bash
mise install
```

---

## Environment Variables

Create:

```bash
backend/.env
```

Example:

```env
DATABASE_URL=postgresql+psycopg://squad:squad@localhost:5432/squad_builder
JWT_SECRET_KEY=your_jwt_secret_key_here
FOOTBALL_DATA_API_TOKEN=your_api_key_here
ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
AUTO_CREATE_TABLES=1
```

Get API key:

https://www.football-data.org/

> For Azure deployment, these environment variables can be stored in Azure App Service configuration or Azure Key Vault references.

---

## Running the Database

Start PostgreSQL:

```bash
make db-up
```

Stop PostgreSQL:

```bash
make db-down
```

---

## Running the Backend

Start the backend development environment (database + API):

```bash
make backend-dev
```

If you only want to start the API and not the database:

```bash
make backend-api
```

Runs on:

```
http://127.0.0.1:8000
```

API Docs:

```
http://127.0.0.1:8000/docs
```

---

## Running the Frontend

Start the frontend development server:

```bash
make frontend-dev
```

Or manually:

```bash
cd frontend
pnpm install
pnpm run dev
```

Runs on:

```
http://localhost:5173
```

---

## First Time Setup

Populate database:

```bash
curl -X POST http://127.0.0.1:8000/refresh \
  -H "Content-Type: application/json" \
  -d '{"competition":["PL"]}'
```

---

## Available Make Commands

Start database:

```bash
make db-up
```

Stop database:

```bash
make db-down
```

Run backend API only:

```bash
make backend-api
```

Run backend development environment (database + API):

```bash
make backend-dev
```

Run frontend development server:

```bash
make frontend-dev
```

Run tests:

```bash
make backend-test
```

---

## Testing

Run backend tests:

```bash
make backend-test
```

Uses:

- pytest
- isolated environment

Example verbose:

```bash
cd backend
uv run pytest -v
```

---

## Development Workflow

Terminal 1:

```bash
make backend-dev
```

Terminal 2:

```bash
make frontend-dev
```

If you want to manage the database separately, use:

```bash
make db-up
```

---

## Azure Deployment Notes

The current production deployment uses the following architecture:

- Frontend: Azure Static Web Apps (Central US)
- Backend: Azure App Service (UK West)
- Database: Azure Database for PostgreSQL Flexible Server (UK West)
- Application Insights: UK West
- CI/CD: GitHub Actions with infrastructure provisioning and app deployment

### Runtime configuration

The backend reads production configuration from App Service settings:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `FOOTBALL_DATA_API_TOKEN`
- `ALLOWED_ORIGINS`
- `AUTO_CREATE_TABLES`

The frontend build receives the backend base URL at build time through:

```bash
VITE_API_BASE=https://squadbuilder-backend-ukwest.azurewebsites.net/api
```

### Workflow behavior

- `main` pushes deploy infrastructure and both applications.
- Manual workflow runs can deploy infrastructure only or deploy infrastructure
  plus apps when `deploy_apps=true`.
- The backend deploy does not rely on a publish profile; it uses Azure login
  credentials from `AZURE_CREDENTIALS`.
- The deployment is designed to preserve the production database and not
  recreate or delete data.

### Secrets required

- `AZURE_CREDENTIALS`
- `AZURE_STATIC_WEB_APPS_API_TOKEN`
- `JWT_SECRET_KEY`
- `FOOTBALL_DATA_API_TOKEN`
- `DATABASE_URL`
- `ALLOWED_ORIGINS`

> Do not store production secrets in source control.

---

## Future improvements

Realistic next steps:

- Replace `AUTO_CREATE_TABLES` with Alembic-based database migrations.
- Add a manually triggered reference-data seeding workflow for refresh jobs.
- Move GitHub Actions to Azure OIDC authentication instead of stored service principal credentials.
- Add real OpenTelemetry/Application Insights instrumentation to backend request traces.
- Support an optional custom domain for the Static Web App.
- Add a secure admin-management command for admin user onboarding and role management.

## Example API Usage

Get players:

```bash
curl "http://127.0.0.1:8000/api/players?nationality=England"
```

Refresh data:

```bash
curl -X POST http://127.0.0.1:8000/api/refresh \
-H "Content-Type: application/json" \
-d '{"competition":["PL"]}'
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

---

## Key Design Decisions

### PostgreSQL

Chosen for:

- production-grade reliability
- relational structure
- industry standard

---

### FastAPI

Benefits:

- fast performance
- automatic OpenAPI docs
- type safety

---

### React + Vite

Benefits:

- fast startup
- modern ecosystem
- strong TypeScript support

---

### Docker

Provides:

- reproducible environment
- isolated database
- simple setup

---

## Future Improvements

Planned features:

- Save squads to database
- User accounts
- Squad sharing links
- Formation view
- Player stats
- Deployment to cloud

---

## What This Project Demonstrates

- Full-stack architecture
- API integration
- Database design
- Backend engineering
- Frontend engineering
- Docker usage
- Testing

---

## Author

Angus Woodman

Software Engineer
Former ocean sailor turned full-stack developer ⚓

---

## License

MIT License
