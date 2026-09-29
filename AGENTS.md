# AGENTS.md

## Project
Data Processing Job Platform / Cloud-Native Document Processing Platform

## Purpose
This repository is a production-oriented learning and portfolio project for building a cloud-native, asynchronous data-processing platform and evolving it toward an AI/agentic platform.

The project should demonstrate practical platform-engineering skills rather than only application development:
- asynchronous job execution
- containerized services
- CI/CD
- observability
- infrastructure automation
- failure handling
- production-readiness
- controlled AI/agent workflows

Codex should treat this file and `docs/architecture.md` as the main project context before making changes.

---

## Current Architecture

### Application stack
- Frontend: React + TypeScript
- Backend API: FastAPI
- Async queue: Redis
- Worker execution: RQ workers
- Database: PostgreSQL
- Data processing: Python / Pandas
- Local runtime: Docker Compose

### Observability
- OpenTelemetry instrumentation
- OpenTelemetry Collector
- Prometheus
- Grafana
- Jaeger

Expected observability flow:

Application / Worker  
→ OpenTelemetry  
→ OpenTelemetry Collector  
→ Prometheus / Jaeger  
→ Grafana

The platform should expose meaningful:
- application metrics
- job metrics
- traces
- structured logs
- health/readiness information

### CI/CD
- GitHub Actions
- self-hosted GitHub Actions runner on WSL
- Docker-based local deployment

Current CI/CD goals:
1. run tests
2. build the application
3. validate containers
4. deploy through the self-hosted WSL runner
5. run smoke/health checks after deployment

Do not remove this pipeline when introducing AI features.

---

## Existing Functional Flow

Typical job lifecycle:

1. User uploads a CSV through the frontend/API.
2. FastAPI validates the request.
3. A job record is created.
4. Work is queued through Redis/RQ.
5. An RQ worker processes the dataset using Python/Pandas.
6. Results/status are persisted in PostgreSQL.
7. The frontend polls the API for job status.
8. Metrics, traces, and logs describe what happened during execution.

Important states should include at least:
- queued
- running
- completed
- failed

Failures must remain inspectable rather than being hidden or automatically retried indefinitely.

---

## Engineering Principles

When modifying the project:

1. Preserve asynchronous processing.
2. Keep the API thin; long-running work belongs in workers.
3. Prefer deterministic infrastructure/workflows for critical execution.
4. AI agents must augment the platform, not replace reliable queueing, CI/CD, observability, or persistence.
5. Keep services independently understandable.
6. Prefer explicit interfaces and contracts between components.
7. Instrument new components with metrics, traces, and structured logs.
8. Add tests for new behavior.
9. Avoid unnecessary framework complexity.
10. Keep the architecture portable toward AWS.

---

## Planned Enhancements

### 1. Production-grade CI/CD
Enhance the existing GitHub Actions pipeline with:
- backend unit tests
- integration tests
- frontend build/test checks
- Docker image build validation
- smoke tests
- deployment health verification
- clean failure reporting
- environment-specific configuration

The goal is to understand the full lifecycle:

code → test → build → deploy → verify → observe

### 2. Stronger observability
Improve visibility across API and workers.

Add or maintain metrics such as:
- request count
- request latency
- job duration
- jobs queued
- jobs completed
- jobs failed
- worker processing time
- uploaded file size
- processing throughput

Tracing should make it possible to follow:

API request  
→ queue operation  
→ worker execution  
→ database interaction

Where possible, correlate logs, metrics, traces, and job IDs.

### 3. Reliability and failure handling
Strengthen:
- retry strategy
- idempotency
- worker failure handling
- job timeouts
- readiness/health checks
- graceful service startup
- dead-letter or failed-job handling where appropriate
- structured error persistence

Retries must be bounded and observable.

### 4. Infrastructure as Code
Introduce Terraform for reproducible infrastructure.

Local Terraform may be used for learning, but the target architecture should map naturally to AWS.

Future cloud mapping:
- FastAPI → ECS/Fargate or container platform
- workers → ECS/Fargate tasks/services
- PostgreSQL → RDS PostgreSQL
- Redis → ElastiCache Redis
- object/file storage → S3
- container images → ECR
- metrics/logging → CloudWatch plus OpenTelemetry-compatible tooling
- public API entry → ALB and/or API Gateway where appropriate

### 5. Agentic backend evolution
The first AI feature should be a controlled **Job Failure Investigator**.

The agent must not directly replace the execution system.

Its role is to analyze operational evidence and produce a diagnosis.

Possible inputs:
- PostgreSQL job record
- application logs
- worker logs
- Prometheus metrics
- Jaeger traces
- exception details
- job metadata

Possible outputs:
- failure summary
- likely root cause
- evidence used
- suggested remediation
- confidence/uncertainty statement

The system should start with deterministic tool calls around the agent.

Potential later tools:
- PostgreSQL query tool
- log lookup tool
- Prometheus metrics tool
- Jaeger trace lookup tool
- CloudWatch query tool
- S3 metadata/result inspection
- ECS task/status lookup

LangGraph or another orchestration framework can be introduced later when there is a clear need for multi-step stateful agent workflows.

Do not introduce multi-agent complexity before one useful agent is reliable.

### 6. Agent observability
Agent behavior should also be observable.

Track:
- agent request count
- latency
- tool calls
- tool failures
- token/model usage where available
- diagnostic result
- trace/span IDs

Agent traces should connect back to the original platform job ID whenever possible.

### 7. Cloud evolution
The long-term project should demonstrate how the local platform maps to a production AWS system.

Relevant AWS concepts/services:
- ECS Fargate
- ECR
- S3
- RDS PostgreSQL
- ElastiCache
- API Gateway / ALB
- Lambda where lightweight event-driven functions are useful
- Step Functions where explicit workflow orchestration is useful
- CloudWatch
- IAM
- VPC
- Terraform

The cloud design should emphasize:
- least privilege
- private networking where appropriate
- explicit service boundaries
- retry/failure semantics
- scalable workers
- cost awareness
- observability

---

## Development Priorities

When choosing the next task, prefer work in roughly this order:

1. Keep current application stable.
2. Expand automated tests.
3. Improve CI/CD.
4. Improve metrics, traces, and structured logs.
5. Harden failure/retry behavior.
6. Add Terraform/infrastructure reproducibility.
7. Add the Job Failure Investigator.
8. Instrument the agent.
9. Map/deploy the architecture to AWS.
10. Only then consider more advanced orchestration or multiple agents.

---

## Instructions for Codex

Before changing code:
1. Read this file.
2. Read `docs/architecture.md`.
3. Inspect the existing implementation instead of assuming filenames or interfaces.
4. Preserve working behavior unless the requested task explicitly changes it.
5. Explain architectural changes that affect component boundaries.
6. Prefer incremental changes over large rewrites.
7. Add/update tests for modified behavior.
8. Keep Docker Compose working.
9. Do not silently remove observability.
10. Do not replace deterministic processing with an LLM.

When implementing AI:
- keep agent code isolated from core job execution
- use tools/functions to access operational data
- validate tool inputs
- handle tool failures explicitly
- make the agent's evidence inspectable
- avoid autonomous destructive actions

---

## Career/Portfolio Intent

This project is intended to demonstrate capability for roles around:
- Cloud Engineer
- Platform Engineer
- Cloud Platform Engineer
- Data & Cloud Engineer
- Cloud-Native Engineer
- Solutions Architecture
- AI Platform / Agentic Platform Engineering

Architectural decisions should therefore favor demonstrable production engineering skills, not just adding features.