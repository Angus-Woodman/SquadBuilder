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
FOOTBALL_DATA_API_TOKEN=your_api_key_here
```

Get API key:

https://www.football-data.org/

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

## Example API Usage

Get players:

```bash
curl "http://127.0.0.1:8000/players?nationality=England"
```

Refresh data:

```bash
curl -X POST http://127.0.0.1:8000/refresh \
-H "Content-Type: application/json" \
-d '{"competition":["PL"]}'
```

Health check:

```bash
curl http://127.0.0.1:8000/health
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
