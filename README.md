# AI Logistics Route Optimizer

Production-grade logistics platform focused on fleet orchestration, intelligent route optimization, operational analytics, and AI-assisted planning workflows.

## Project Overview

AI Logistics is designed to help logistics teams plan, execute, and monitor delivery operations through:

- Driver, vehicle, and order lifecycle management
- Constraint-aware route optimization
- Operations analytics and utilization tracking
- AI module foundation for demand and ETA prediction
- Containerized, cloud-deployable architecture

This project is structured for both real-world deployment and portfolio presentation.

## Features

- Authentication-ready backend with token support
- Fleet operations dashboard and analytics UI
- Route Optimization workflow with map visualization
- Reusable data table and form architecture for operations entities
- Service-layer API integration for frontend modules
- PostgreSQL persistence with Alembic migrations
- Docker and docker-compose based local orchestration
- Render-ready backend deployment configuration

## Architecture

### High-level Flow

1. React frontend consumes backend APIs.
2. FastAPI backend handles business workflows and orchestration.
3. SQLAlchemy + PostgreSQL manage operational data.
4. Alembic manages schema migration lifecycle.
5. Optimization and AI modules operate as internal service domains.

### Runtime Components

- Frontend: React 19 + Vite + TailwindCSS
- Backend: FastAPI + SQLAlchemy + Alembic
- Database: PostgreSQL
- Containerization: Docker + docker-compose
- Deployment: Render (backend)

## Folder Structure

```text
AI-Logistics/
	alembic/
		versions/
	backend/
		app/
			ai/
			analytics/
			api/
			core/
			db/
			dependencies/
			middleware/
			models/
			optimization/
			repositories/
			schemas/
			services/
			utils/
			main.py
	frontend/
		src/
			components/
			context/
			pages/
			services/
	datasets/
	deployment/
	docs/
	notebook/
	smart-logistics/
	vroom/
	Dockerfile
	docker-compose.yml
	render.yaml
	.env.example
	requirements.txt
```

## Technology Stack

### Backend

- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic Settings
- psycopg

### Frontend

- React 19
- Vite
- TailwindCSS
- React Router
- Recharts
- Leaflet + React Leaflet
- Axios

### DevOps

- Docker
- docker-compose
- Render

## Installation

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm
- PostgreSQL 15+
- Docker (optional but recommended)

### Clone

```bash
git clone <your-repository-url>
cd AI-Logistics
```

## Backend Setup

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Copy environment template:

```bash
cp .env.example .env
```

Run backend:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to Vite local dev server.

## Environment Variables

Define these in `.env` (see `.env.example`):

- `APP_NAME`
- `ENVIRONMENT`
- `DEBUG`
- `SECRET_KEY`
- `ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `DATABASE_URL`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
- `BACKEND_CORS_ORIGINS`
- `API_HOST`
- `API_PORT`
- `FRONTEND_URL`
- `VITE_API_BASE_URL`

## Database Migration

Apply migrations:

```bash
alembic upgrade head
```

Create a new migration revision:

```bash
alembic revision --autogenerate -m "describe change"
```

Rollback one migration:

```bash
alembic downgrade -1
```

## API Endpoints

Core endpoint groups:

- Authentication: `/auth/*`
- Drivers: `/drivers`
- Vehicles: `/vehicles`
- Orders: `/orders`
- Optimization: `/optimization/optimize`
- Analytics: `/analytics/dashboard`

Interactive docs (when backend is running):

- Swagger UI: `/docs`
- ReDoc: `/redoc`

## Optimization Module

Optimization module responsibilities:

- Driver/vehicle/order assignment orchestration
- Route sequencing and stop ordering
- Distance and load summary generation
- Map-friendly route output for frontend visualization

Frontend integration:

- Input selection of drivers, vehicles, and orders
- API call to optimization endpoint
- Route cards with stop-level details
- Leaflet map route plotting and bounds fitting

## Analytics Module

Analytics module responsibilities:

- Fleet utilization tracking
- Driver and vehicle performance KPIs
- Route efficiency and on-time delivery visibility
- Dashboard metric aggregation for operations monitoring

Frontend integration:

- Dashboard cards and charts
- Analytics KPI panels
- Recharts-based trend visualization

## AI Prediction Module

AI module foundation supports:

- Demand forecasting pipelines
- ETA prediction enhancements
- Dynamic risk scoring for delivery delays
- Model-serving integration paths with operational APIs

This module is designed for iterative expansion and production ML workflow integration.

## Deployment Instructions

### Docker Compose (local full stack)

```bash
docker compose up --build
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:4173`
- PostgreSQL: `localhost:5432`

### Render (backend)

`render.yaml` is included for backend deployment as a web service.

Typical workflow:

1. Push repository to GitHub.
2. Create a new Render Blueprint from repository.
3. Configure environment values (or sync from dashboard).
4. Deploy and monitor logs.

## Screenshots

Add UI screenshots for portfolio use:

- Login
- Dashboard
- Analytics
- Route Optimization Form
- Route Cards
- Map View

Suggested structure:

```text
docs/screenshots/
	login.png
	dashboard.png
	analytics.png
	optimization-form.png
	optimization-results.png
	route-map.png
```

## Future Improvements

- Real-time GPS tracking integration
- WebSocket-based live operations updates
- Constraint tuning UI for optimization parameters
- Advanced forecasting dashboards
- Multi-tenant org/workspace model
- Role-based access control hardening
- CI/CD pipelines with automated tests and security scans
- Observability stack (metrics, logs, traces)

## License

Define and add your preferred license before public distribution.

