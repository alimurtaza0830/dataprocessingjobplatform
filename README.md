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

Start the development environment:

~~~bash
docker compose up --build -d
~~~

Check all containers:

~~~bash
docker compose ps
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
docker compose logs -f backend
~~~

View worker logs:

~~~bash
docker compose logs -f worker
~~~

## Production-style local environment

Start the Nginx production frontend:

~~~bash
docker compose --profile production up --build -d
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

## Automated testing

Run all backend tests:

~~~bash
docker compose run --rm backend \
  python -m pytest -v
~~~

Run frontend linting:

~~~bash
docker compose exec frontend npm run lint
~~~

Run frontend tests:

~~~bash
docker compose exec frontend npm test
~~~

Run the frontend production build:

~~~bash
docker compose exec frontend npm run build
~~~

Run the backend smoke test:

~~~bash
./scripts/backend_smoke_test.sh
~~~

Run the production end-to-end smoke test:

~~~bash
./scripts/production_smoke_test.sh
~~~

Run every validation step:

~~~bash
./scripts/validate_project.sh
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
  --form "uploaded_file=@empty.csv"
~~~

The worker changes the job status to `failed` and stores an error such as:

~~~text
The uploaded CSV is empty or has no readable columns
~~~

Stop the worker:

~~~bash
docker compose stop worker
~~~

New jobs remain pending in Redis.

Restart the worker:

~~~bash
docker compose start worker
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
