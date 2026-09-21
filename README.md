# Data Quality Platform

A containerized full-stack application that accepts CSV files, processes them asynchronously, and generates data-quality reports.

The project demonstrates React, FastAPI, PostgreSQL, Redis, background workers, Docker, automated testing, and production-style container deployment.

## Purpose

Users can upload a CSV file and receive a report containing:

- Row and column counts
- Column names and detected data types
- Missing values per column
- Total missing values
- Duplicate-row count
- Numeric minimum, maximum, mean, and median

CSV processing happens asynchronously so that the API does not remain blocked while the file is analyzed.

## Architecture

~~~text
Browser
  |
  v
React frontend
  |
  v
Nginx reverse proxy
  |
  v
FastAPI backend
  |                |
  |                v
  |              Redis queue
  |                |
  v                v
PostgreSQL       RQ worker
                   |
                   v
             Pandas analysis
                   |
                   v
              PostgreSQL
~~~

## Application workflow

1. The user selects a CSV file.
2. React uploads it to FastAPI.
3. FastAPI stores the uploaded file.
4. FastAPI creates a PostgreSQL job record.
5. FastAPI places the job ID in Redis.
6. The RQ worker retrieves the queued job.
7. Pandas analyzes the CSV.
8. The worker stores the report or error in PostgreSQL.
9. React polls the job-status endpoint.
10. React displays the completed report or failure message.

## Job lifecycle

~~~text
pending
   |
   v
processing
   |
   +----> completed
   |
   +----> failed
~~~

Failed jobs retain their error message so failures are visible through both the API and frontend.

## Services

| Service | Purpose |
|---|---|
| React | User interface, file upload, status polling, and reports |
| Nginx | Serves the production frontend and proxies API requests |
| FastAPI | Handles uploads, validation, job management, and REST APIs |
| PostgreSQL | Stores job metadata, reports, timestamps, and errors |
| Redis | Holds temporary background-processing jobs |
| RQ worker | Processes queued CSV jobs |
| Pandas | Performs the data-quality analysis |
| Alembic | Applies database schema migrations |
| Docker Compose | Orchestrates the local application containers |

## Data-quality report

The generated report currently includes:

- Number of rows
- Number of columns
- Column names
- Detected data types
- Missing values by column
- Total missing values
- Duplicate rows
- Numeric minimum
- Numeric maximum
- Numeric mean
- Numeric median

## Local development

Create a local environment file from the example:

~~~bash
cp .env.example .env
~~~

The sample values are intended for local development only. For production-like deployments, provide private values through `.env`, CI/CD secrets, Docker secrets, or a platform secret manager.

Start the development environment:

~~~bash
docker compose --env-file .env up --build -d
~~~

Compose starts PostgreSQL, Redis, a one-shot upload-volume initializer, a one-shot Alembic migration service, the FastAPI backend, the RQ worker, and the Vite frontend.

Check all containers:

~~~bash
docker compose --env-file .env ps
~~~

Open the development frontend:

~~~text
http://localhost:5173
~~~

Open the FastAPI documentation:

~~~text
http://localhost:8000/docs
~~~

View backend logs:

~~~bash
docker compose --env-file .env logs -f backend
~~~

View worker logs:

~~~bash
docker compose --env-file .env logs -f worker
~~~

Run database migrations manually:

~~~bash
docker compose --env-file .env run --rm backend-migrate
~~~

## Production-style local environment

Start the Nginx production frontend:

~~~bash
docker compose --env-file .env --profile production up --build -d \
  database \
  redis \
  storage-init \
  backend-migrate \
  backend \
  worker \
  frontend-prod
~~~

Open the production frontend:

~~~text
http://localhost:8080
~~~

Check the Nginx health endpoint:

~~~bash
curl http://localhost:8080/health
~~~

Check the backend through the Nginx reverse proxy:

~~~bash
curl -s http://localhost:8080/api/health/ready \
  | python3 -m json.tool
~~~

## Main API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/jobs/upload` | Upload and queue a CSV file |
| `GET` | `/jobs` | List all processing jobs |
| `GET` | `/jobs/{job_id}` | Retrieve job status and metadata |
| `GET` | `/jobs/{job_id}/report` | Retrieve the completed report |
| `GET` | `/health` | Check FastAPI liveness |
| `GET` | `/health/database` | Check PostgreSQL connectivity |
| `GET` | `/health/redis` | Check Redis connectivity |
| `GET` | `/health/ready` | Check complete backend readiness |

## Configuration

The main runtime settings are defined in `.env.example`.

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy/PostgreSQL connection string used by the backend, worker, and migrations |
| `POSTGRES_DB` | Local PostgreSQL database name |
| `POSTGRES_USER` | Local PostgreSQL username |
| `POSTGRES_PASSWORD` | Local PostgreSQL password |
| `REDIS_URL` | Redis connection string used by the backend and worker |
| `UPLOAD_DIRECTORY` | Container path where uploaded CSV files are stored |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins for the FastAPI backend |
| `MAX_UPLOAD_BYTES` | Maximum uploaded CSV size; default example is 25 MB |
| `MAX_CSV_ROWS` | Maximum accepted CSV rows during analysis |
| `MAX_CSV_COLUMNS` | Maximum accepted CSV columns during analysis |
| `BACKEND_PORT` | Host port for FastAPI |
| `FRONTEND_DEV_PORT` | Host port for the Vite frontend |
| `FRONTEND_PROD_PORT` | Host port for the Nginx production frontend |
| `POSTGRES_HOST_PORT` | Host port for PostgreSQL in local development |
| `REDIS_HOST_PORT` | Host port for Redis in local development |

## Automated testing

Run all backend tests:

~~~bash
docker compose --env-file .env --profile test run --rm backend-test \
  python -m pytest -v
~~~

Run frontend linting:

~~~bash
docker compose --env-file .env exec frontend npm run lint
~~~

Run frontend tests:

~~~bash
docker compose --env-file .env exec frontend npm test
~~~

Run the frontend production build:

~~~bash
docker compose --env-file .env exec frontend npm run build
~~~

Run the production end-to-end smoke test:

~~~bash
./scripts/production_smoke_test.sh
~~~

Run every validation step:

~~~bash
./scripts/validate_project.sh
~~~

By default, `validate_project.sh` uses `.env.example`. To validate with another env file:

~~~bash
COMPOSE_ENV_FILE=.env ./scripts/validate_project.sh
~~~

## Failure simulation

Create an empty CSV:

~~~bash
touch empty.csv
~~~

Upload it:

~~~bash
curl --request POST \
  http://localhost:8000/jobs/upload \
  --form "uploaded_file=@empty.csv;type=text/csv"
~~~

Invalid CSV files are rejected before they are queued. The API returns a validation error such as:

~~~text
The uploaded CSV is empty or has no readable columns
~~~

Stop the worker:

~~~bash
docker compose --env-file .env stop worker
~~~

New jobs remain pending in Redis.

Restart the worker:

~~~bash
docker compose --env-file .env start worker
~~~

The queued jobs will then be processed.

## Frontend modes

### Development mode

~~~text
React source
    |
    v
Vite development server
    |
    v
Hot reload on localhost:5173
~~~

### Production mode

~~~text
React source
    |
    v
TypeScript and Vite build
    |
    v
Static files
    |
    v
Nginx on localhost:8080
~~~

## Technology stack

### Frontend

- React
- TypeScript
- Vite
- Vitest
- Testing Library
- Nginx

### Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- Psycopg
- Pandas
- Pytest
- HTTPX

### Infrastructure

- Docker
- Docker Compose
- PostgreSQL
- Redis
- RQ

## Planned DevOps phases

The next project phases will add:

1. Git and GitHub repository setup
2. GitHub Actions continuous integration
3. A WSL self-hosted GitHub Actions runner
4. Automated local deployment
5. OpenTelemetry instrumentation
6. Prometheus metrics
7. Grafana dashboards
8. Jaeger distributed tracing
9. Datadog integration and comparison
10. Terraform-managed infrastructure
11. Optional AWS deployment

## Portfolio explanation

The Data Quality Platform is a containerized full-stack application that processes uploaded CSV files asynchronously. React provides the user interface, FastAPI manages uploads and job APIs, PostgreSQL stores job state, Redis coordinates background work, and an RQ worker performs Pandas-based analysis.

The project includes development and production containers, health checks, failure handling, unit tests, integration tests, frontend component tests, and end-to-end smoke testing. It demonstrates the complete path from application development to CI/CD, observability, and Infrastructure as Code.
