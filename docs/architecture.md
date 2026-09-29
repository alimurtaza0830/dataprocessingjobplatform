# System Architecture

## 1. Purpose of This Document

This document describes the architecture of the Data Processing Job Platform and its planned evolution into a cloud-native, production-oriented, AI-enabled platform.

The purpose of the project is not only to process uploaded CSV files. The larger goal is to demonstrate how a modern production system can combine:

- frontend and backend application development
- asynchronous job processing
- queues and workers
- relational persistence
- observability
- CI/CD
- infrastructure automation
- cloud architecture
- reliability engineering
- AI-assisted operations
- agentic workflows
- production deployment patterns

The current platform runs locally using Docker Compose and is intentionally designed so that its major components can later be migrated to AWS without rewriting the entire application.

The architecture should therefore remain:

- modular
- observable
- testable
- asynchronous
- cloud-portable
- failure-aware
- incrementally extensible

The system should not become unnecessarily complex simply to demonstrate additional technologies. New components should only be introduced when they solve a clear architectural problem.

---

# 2. Project Goals

The platform should demonstrate the ability to build and operate a production-oriented cloud-native system.

The primary engineering goals are:

1. Build a clean frontend and backend separation.
2. Keep long-running work outside the HTTP request lifecycle.
3. Use asynchronous workers for processing jobs.
4. Persist job state in a durable database.
5. Provide useful observability across services.
6. Build a real CI/CD pipeline rather than manually deploying changes.
7. Introduce reliable failure handling and retries.
8. Add infrastructure as code.
9. Map the local architecture cleanly to AWS.
10. Add AI capabilities without allowing an LLM to become responsible for deterministic infrastructure behavior.
11. Demonstrate agentic workflows for operational investigation and automation.
12. Keep the system understandable enough that architectural decisions can be explained during interviews, client discussions, or architecture reviews.

---

# 3. Architectural Philosophy

The project follows several core architectural principles.

## 3.1 Long-running work must be asynchronous

HTTP requests should remain short-lived.

The backend should not keep the user waiting while large datasets are processed.

Instead:

```text
Client request
    ↓
API accepts the request
    ↓
Job is created
    ↓
Job is placed on a queue
    ↓
Worker processes the job asynchronously
    ↓
Client polls or receives status updates
```

This pattern allows the API and worker layer to scale independently.

---

## 3.2 Persistent state must not live only in memory

Job information must survive process restarts.

Important information such as:

- job status
- creation time
- execution time
- input metadata
- failure reason
- output metadata
- retry count

should be stored persistently.

PostgreSQL currently serves this purpose.

---

## 3.3 Observability is part of the architecture

Metrics, logs, and traces are not optional debugging utilities.

They are first-class system capabilities.

Every important workflow should be observable.

A production system should allow an engineer to answer:

- What request created this job?
- How long did the API take?
- How long did the worker take?
- Why did the worker fail?
- Was the database slow?
- Was Redis unavailable?
- How many jobs are failing?
- Which service caused the problem?
- Can the request and background job be correlated?

---

## 3.4 AI should augment deterministic systems

Core execution behavior should remain deterministic.

For example:

```text
job submission
queueing
database writes
worker retries
job execution
status updates
authentication
authorization
deployment
health checks
```

should not depend on an LLM deciding what to do.

AI should instead be used where interpretation, reasoning, or flexible analysis is useful.

The first example is an AI-powered Job Failure Investigator.

---

## 3.5 Prefer incremental architecture

The system should evolve gradually.

The target is not:

```text
simple app
↓
massive microservice rewrite
↓
multi-agent system
↓
complex Kubernetes deployment
```

The preferred approach is:

```text
working local app
↓
reliable tests
↓
CI/CD
↓
observability
↓
failure handling
↓
infrastructure as code
↓
cloud deployment
↓
AI-assisted operations
↓
advanced orchestration where justified
```

---

# 4. Current Technology Stack

The current platform uses the following technologies.

## Frontend

- React
- TypeScript
- browser-based application
- REST communication with the backend

Responsibilities:

- file upload
- job creation
- job status display
- result display
- error display
- potential future operational dashboard

---

## Backend API

- Python
- FastAPI

Responsibilities:

- expose REST APIs
- validate requests
- accept uploaded files
- create jobs
- persist metadata
- enqueue background work
- return job identifiers
- expose job status
- expose health endpoints
- provide future agent endpoints

The backend should remain relatively thin.

Large processing logic should not be embedded directly in request handlers.

---

## Job Queue

- Redis
- RQ

Responsibilities:

- queue asynchronous jobs
- decouple API from workers
- temporarily buffer workload
- allow multiple workers to consume jobs

---

## Worker

- Python
- RQ worker
- Pandas for data processing

Responsibilities:

- retrieve queued jobs
- execute data-processing logic
- update status
- persist results
- record errors
- emit metrics
- emit traces
- emit structured logs

---

## Database

- PostgreSQL

Responsibilities:

- persistent job state
- execution metadata
- result metadata
- failure information
- future user or tenant data
- potentially agent investigation records

---

## Container Runtime

- Docker
- Docker Compose

Responsibilities:

- reproduce the development environment
- run services consistently
- isolate dependencies
- simulate service boundaries
- provide a local environment similar to future cloud deployment

---

## Observability Stack

- OpenTelemetry
- OpenTelemetry Collector
- Prometheus
- Grafana
- Jaeger

Responsibilities:

- metrics
- distributed tracing
- visualization
- performance analysis
- debugging
- correlation across services

---

## CI/CD

- GitHub Actions
- self-hosted GitHub Actions runner
- WSL-based deployment environment

Responsibilities:

- execute automated tests
- validate builds
- build containers
- deploy the application
- verify deployment health
- reduce manual deployment steps

---

# 5. Current Logical Architecture

The current application architecture can be represented as follows:

```text
                         ┌────────────────────────┐
                         │        Browser         │
                         │                        │
                         │ React + TypeScript     │
                         └───────────┬────────────┘
                                     │
                                     │ HTTP / REST
                                     │
                                     ▼
                         ┌────────────────────────┐
                         │       FastAPI API      │
                         │                        │
                         │ Request validation     │
                         │ Job management         │
                         │ Upload handling        │
                         │ Status endpoints       │
                         └───────────┬────────────┘
                                     │
                    ┌────────────────┼─────────────────┐
                    │                │                 │
                    │                │                 │
                    ▼                ▼                 ▼
             ┌────────────┐    ┌────────────┐   Telemetry
             │ PostgreSQL │    │   Redis    │
             │            │    │            │
             │ Job state  │    │ RQ queues  │
             └────────────┘    └─────┬──────┘
                                     │
                                     │ queued jobs
                                     │
                                     ▼
                              ┌───────────────┐
                              │   RQ Worker   │
                              │               │
                              │ Python        │
                              │ Pandas        │
                              └───────┬───────┘
                                      │
                                      │
                                      ▼
                               Data Processing
                                      │
                                      ▼
                                Result / Error
                                      │
                                      ▼
                                PostgreSQL
```

---

# 6. Request and Job Flow

The normal lifecycle of a job is:

```text
User selects file
        ↓
Frontend sends upload request
        ↓
FastAPI validates request
        ↓
Backend creates job ID
        ↓
Backend creates job record in PostgreSQL
        ↓
Job is queued through Redis/RQ
        ↓
API returns job ID
        ↓
Worker retrieves job
        ↓
Worker changes status to RUNNING
        ↓
Worker processes file
        ↓
Worker generates result
        ↓
Worker stores result metadata
        ↓
Worker changes status to COMPLETED
        ↓
Frontend polls job endpoint
        ↓
Frontend shows result
```

If processing fails:

```text
Worker encounters exception
        ↓
Exception is logged
        ↓
Trace/span is marked as failed
        ↓
Relevant metrics are updated
        ↓
Job status becomes FAILED
        ↓
Failure details are persisted
        ↓
Frontend displays failure state
```

---

# 7. Job State Model

The minimum job states are:

```text
QUEUED
RUNNING
COMPLETED
FAILED
```

A future state model may include:

```text
QUEUED
RUNNING
RETRYING
COMPLETED
FAILED
TIMED_OUT
CANCELLED
```

A valid lifecycle may look like:

```text
QUEUED
  ↓
RUNNING
  ↓
COMPLETED
```

or:

```text
QUEUED
  ↓
RUNNING
  ↓
FAILED
```

or:

```text
QUEUED
  ↓
RUNNING
  ↓
RETRYING
  ↓
RUNNING
  ↓
COMPLETED
```

State transitions should be explicit.

The worker should not silently fail without updating persistent state.

---

# 8. Job Data Model Direction

The exact database schema may evolve, but conceptually a job should contain information such as:

```text
job_id
status
created_at
started_at
completed_at
input_filename
input_size
result_location
error_type
error_message
retry_count
worker_id
trace_id
```

Future additions may include:

```text
tenant_id
user_id
workflow_id
agent_investigation_id
cloud_task_id
s3_input_key
s3_result_key
```

The database should contain enough information to reconstruct what happened without depending only on logs.

---

# 9. Asynchronous Processing Model

The use of Redis and RQ separates the request layer from the execution layer.

This creates several advantages.

## API responsiveness

The API can return quickly rather than blocking while processing occurs.

---

## Independent scaling

The API and workers can scale separately.

Example:

```text
2 API containers
10 worker containers
```

if processing load becomes heavier than request traffic.

---

## Failure isolation

A worker failure should not crash the API service.

---

## Queue buffering

If 100 jobs arrive at once, Redis can buffer them while workers process them gradually.

---

## Future cloud migration

The same architectural concept maps to cloud systems such as:

```text
Redis/RQ
```

becoming alternatives like:

```text
Amazon SQS
ECS workers
AWS Batch
Step Functions
```

depending on workload characteristics.

---

# 10. Observability Architecture

The current observability system uses OpenTelemetry as a common instrumentation layer.

The high-level flow is:

```text
FastAPI ────────────────┐
                        │
RQ Worker ──────────────┼───────────────┐
                        │               │
Database instrumentation│               │
                        │               ▼
                        │     OpenTelemetry Collector
                        │               │
                        │      ┌────────┴─────────┐
                        │      │                  │
                        ▼      ▼                  ▼
                    Traces  Metrics             Logs
                        │      │
                        ▼      ▼
                     Jaeger  Prometheus
                        │      │
                        └──┬───┘
                           ▼
                         Grafana
```

---

# 11. Metrics

Metrics should answer operational questions.

Recommended metrics include:

## API metrics

```text
http_requests_total
http_request_duration_seconds
http_request_errors_total
```

Useful dimensions may include:

```text
route
method
status_code
```

---

## Job metrics

```text
jobs_submitted_total
jobs_started_total
jobs_completed_total
jobs_failed_total
job_processing_duration_seconds
```

---

## Worker metrics

```text
worker_jobs_processed_total
worker_jobs_failed_total
worker_processing_duration_seconds
```

---

## Queue metrics

Potential queue metrics:

```text
queue_depth
queued_jobs
oldest_queued_job_age
```

---

## Upload metrics

Example:

```text
data_quality_upload_size_bytes
```

This can help visualize:

- average upload size
- unusually large uploads
- relationship between upload size and processing duration

---

# 12. Distributed Tracing

Tracing should allow engineers to understand how one request moves through the system.

Ideal flow:

```text
HTTP Upload Request
       ↓
FastAPI Span
       ↓
Database Job Creation
       ↓
Redis Enqueue
       ↓
Worker Job Span
       ↓
Database Read/Write
       ↓
Processing Logic
```

Because RQ introduces an asynchronous boundary, trace context may not automatically propagate.

Therefore the platform should maintain correlation using:

```text
job_id
trace_id
correlation_id
```

A practical pattern is:

```text
API receives request
        ↓
trace created
        ↓
job_id created
        ↓
job_id stored in trace attributes
        ↓
job_id included in queued payload
        ↓
worker starts new span
        ↓
worker includes job_id as attribute
```

Even if both operations do not appear as one continuous distributed trace, the job ID creates an operational correlation mechanism.

---

# 13. Logging

Logs should eventually be structured.

Example:

```json
{
  "timestamp": "2026-09-26T12:00:00Z",
  "level": "ERROR",
  "service": "worker",
  "job_id": "abc123",
  "trace_id": "xyz456",
  "event": "job_failed",
  "error_type": "ValueError",
  "message": "CSV column validation failed"
}
```

Structured logs make it easier to:

- search
- aggregate
- correlate
- send logs to cloud platforms
- expose logs to the AI investigation layer

The current local environment may still output logs to container stdout, but the format should remain compatible with future centralized logging.

---

# 14. Health and Readiness

Each important service should expose or provide clear health information.

For FastAPI:

```text
/health
/readiness
```

Possible semantics:

## `/health`

Answers:

> Is this process alive?

Example response:

```json
{
  "status": "ok"
}
```

## `/readiness`

Answers:

> Can this instance actually serve requests?

Readiness may verify:

- PostgreSQL connection
- Redis connection
- internal dependencies

The deployment process should use readiness rather than only checking whether the container started.

---

# 15. Current CI/CD Architecture

The current CI/CD environment uses GitHub Actions and a self-hosted runner.

Conceptually:

```text
Developer
    ↓
git push / pull request
    ↓
GitHub
    ↓
GitHub Actions
    ↓
Automated Tests
    ↓
Build Validation
    ↓
Deployment Workflow
    ↓
Self-hosted WSL Runner
    ↓
Docker Compose Deployment
    ↓
Health Check
    ↓
Smoke Test
```

---

# 16. CI Pipeline

The CI pipeline should eventually include:

```text
Checkout
   ↓
Install dependencies
   ↓
Lint
   ↓
Unit tests
   ↓
Integration tests
   ↓
Frontend build
   ↓
Docker build
   ↓
Container validation
```

The pipeline should fail immediately if an essential validation step fails.

---

# 17. Deployment Pipeline

A local deployment workflow can look like:

```text
GitHub Actions
    ↓
Self-hosted WSL runner
    ↓
Pull latest repository
    ↓
docker compose build
    ↓
docker compose up -d
    ↓
Wait for readiness
    ↓
Run smoke tests
```

The goal is to simulate a real deployment lifecycle.

Future cloud deployment may replace the final stage with:

```text
Build image
    ↓
Push to ECR
    ↓
Terraform / ECS deployment
    ↓
Wait for ECS health
    ↓
Smoke test public endpoint
```

---

# 18. Testing Strategy

The application should gradually develop several testing layers.

## Unit tests

Used for:

- validation functions
- processing logic
- utility functions
- business rules
- data transformation

---

## Integration tests

Used for:

- API + PostgreSQL
- API + Redis
- job submission
- invalid uploads
- missing jobs
- empty CSV handling
- worker behavior

---

## End-to-end tests

Future tests can validate:

```text
upload file
    ↓
job created
    ↓
job processed
    ↓
status completed
    ↓
result available
```

---

## Smoke tests

Post-deployment validation should verify:

- API is reachable
- health endpoint works
- required containers are alive
- a minimal request works

---

# 19. Reliability Architecture

Reliability should evolve beyond simply catching exceptions.

Key concerns include:

- retries
- idempotency
- timeouts
- partial failures
- duplicate requests
- worker crashes
- container restarts
- queue failures
- database unavailability

---

# 20. Retry Strategy

Retries should be bounded.

Bad behavior:

```text
fail
↓
retry forever
↓
consume resources indefinitely
```

Preferred behavior:

```text
attempt 1
↓
attempt 2
↓
attempt 3
↓
mark FAILED
```

Retry attempts should be observable.

The system should distinguish transient problems from permanent errors.

Example transient problems:

- temporary database connection problem
- external API timeout
- temporary network error

Example permanent problems:

- malformed CSV
- unsupported schema
- missing required column
- invalid user input

Permanent failures should generally not be retried automatically.

---

# 21. Idempotency

Job processing should avoid producing duplicate side effects.

For example, if a worker restarts after partially completing a job, rerunning the same job should not create duplicate outputs unnecessarily.

Possible approaches:

- stable job identifiers
- unique database constraints
- deterministic result paths
- checking job state before execution
- idempotency keys

---

# 22. Failure Persistence

Failures should be stored, not merely logged.

A job failure record may include:

```text
job_id
failure_timestamp
error_type
error_message
stack_trace_reference
retry_count
worker_id
trace_id
```

This becomes particularly important for the future AI failure investigation capability.

---

# 23. Infrastructure as Code

Terraform should eventually be introduced as the primary infrastructure definition language.

The goal is reproducibility.

Infrastructure should not depend on someone remembering which buttons were clicked in the AWS console.

Terraform should eventually define:

- VPC
- public/private subnets
- security groups
- IAM roles
- ECS cluster
- ECS services
- ECS task definitions
- ECR repositories
- RDS PostgreSQL
- ElastiCache Redis
- S3 buckets
- load balancer
- CloudWatch configuration
- relevant secrets integration

---

# 24. Target AWS Architecture

A future AWS version may look like this:

```text
                             Internet
                                │
                                ▼
                     ┌─────────────────────┐
                     │ API Gateway or ALB  │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ FastAPI on ECS      │
                     │ Fargate             │
                     └──────────┬──────────┘
                                │
              ┌─────────────────┼───────────────────┐
              │                 │                   │
              ▼                 ▼                   ▼
        RDS PostgreSQL     ElastiCache Redis        S3
                                │
                                │
                                ▼
                       ┌─────────────────┐
                       │ Worker Service  │
                       │ ECS Fargate     │
                       └─────────────────┘
```

Supporting services:

```text
ECR
IAM
VPC
CloudWatch
Terraform
Secrets Manager / Parameter Store
```

---

# 25. AWS Service Mapping

The current local components map approximately as follows.

| Local Component | AWS Direction |
|---|---|
| React frontend | S3 + CloudFront or another frontend hosting platform |
| FastAPI | ECS Fargate |
| Docker images | ECR |
| PostgreSQL | RDS PostgreSQL |
| Redis | ElastiCache Redis |
| Worker containers | ECS Fargate |
| File storage | S3 |
| Local logs | CloudWatch Logs |
| Prometheus/Grafana | Managed or self-hosted observability options |
| Docker Compose | ECS services/tasks |
| Manual infrastructure | Terraform |
| Local secrets | Secrets Manager / Parameter Store |

This mapping is conceptual and should not force unnecessary services into the application.

---

# 26. API Gateway vs ALB Direction

The exact API entry point depends on architecture.

An ALB fits well when:

- FastAPI runs continuously on ECS
- HTTP routing is simple
- containers need direct load balancing

API Gateway may be useful when:

- API management is important
- authentication/throttling is required
- Lambda integration is used
- externally managed APIs are preferred

The system should not use both unless there is a clear architectural reason.

---

# 27. Lambda Usage

Lambda should be used for lightweight event-driven functions.

Good examples:

- presigned URL generation
- metadata transformation
- event handling
- lightweight orchestration helpers
- scheduled maintenance tasks

Lambda should not be used for long-running heavy CSV processing when ECS/Fargate is a better fit.

---

# 28. Step Functions Usage

Step Functions become valuable when processing evolves from:

```text
one job
↓
one worker
```

to:

```text
job
↓
validation
↓
parallel processing
↓
aggregation
↓
verification
↓
result publication
```

A deterministic multi-stage workflow could then be:

```text
API
 ↓
Step Functions
 ↓
Validate Input
 ↓
Run Processing Task A
 ↓
Run Processing Task B
 ↓
Merge Results
 ↓
Verify Output
 ↓
Complete Job
```

Step Functions should not be introduced simply because they are available.

Use them when workflow state transitions, retries, branching, or parallel stages become substantial enough to justify explicit orchestration.

---

# 29. Event-Driven Architecture Direction

Future extensions may use:

- EventBridge
- SNS
- SQS

These services solve different problems.

## EventBridge

Useful for event routing.

Example:

```text
JobCompleted event
      ↓
EventBridge
      ↓
multiple interested consumers
```

---

## SNS

Useful for fan-out notifications.

Example:

```text
ProcessingCompleted
      ↓
SNS
      ├─ email notification
      ├─ SQS consumer A
      └─ SQS consumer B
```

---

## SQS

Useful for durable asynchronous work queues.

Example:

```text
API
 ↓
SQS
 ↓
Worker
```

SQS may eventually replace Redis/RQ if the system becomes more AWS-native.

---

# 30. Agentic Evolution

The next major enhancement is to add AI capabilities to the platform.

The goal is not to convert the entire system into an "AI application."

Instead, AI should solve specific problems where reasoning over operational information is useful.

The first planned agent is:

# Job Failure Investigator

The purpose of this agent is to analyze why a background processing job failed.

A user or operator should eventually be able to ask:

```text
Why did job abc123 fail?
```

The system should not simply send the job ID to an LLM.

The agent must gather evidence using tools.

---

# 31. Job Failure Investigator Architecture

Conceptually:

```text
                         User / Operator
                               │
                               ▼
                    Investigation Endpoint
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Failure Investigator│
                    │       Agent         │
                    └─────────┬───────────┘
                              │
                              │ tool calls
                              │
           ┌──────────────────┼───────────────────┐
           │                  │                   │
           ▼                  ▼                   ▼
     Job Database Tool     Logs Tool        Metrics Tool
           │                  │                   │
           └──────────────────┼───────────────────┘
                              │
                              ▼
                          Trace Tool
                              │
                              ▼
                         Jaeger / OTel
```

---

# 32. Agent Investigation Workflow

A possible flow:

```text
Receive job_id
      ↓
Fetch job record
      ↓
Check status and timestamps
      ↓
Retrieve failure metadata
      ↓
Retrieve relevant logs
      ↓
Retrieve metrics around failure time
      ↓
Retrieve trace information
      ↓
Correlate evidence
      ↓
Generate diagnosis
      ↓
Return likely cause
      ↓
Return supporting evidence
      ↓
Return suggested remediation
```

The result should be grounded in retrieved evidence.

---

# 33. Agent Output Format

A structured investigation response could contain:

```json
{
  "job_id": "abc123",
  "summary": "The worker failed while parsing the uploaded CSV.",
  "likely_cause": "The uploaded file did not contain the required 'price' column.",
  "evidence": [
    "Worker log contains KeyError: price",
    "Job status changed to FAILED after 1.8 seconds",
    "Trace shows failure inside transform_dataset"
  ],
  "suggested_action": "Validate required CSV columns before enqueueing the job.",
  "confidence": "high"
}
```

The output should clearly separate:

- observations
- inference
- recommendation

---

# 34. Agent Tools

The agent should access operational systems through explicit tools.

Initial conceptual tools:

```text
get_job(job_id)
get_job_logs(job_id)
get_job_metrics(job_id, time_window)
get_job_trace(job_id)
```

These tool boundaries are important.

The LLM should not have unrestricted access to the database.

Instead, application code should expose narrow, controlled interfaces.

---

# 35. Example Tool Contracts

## `get_job`

Input:

```json
{
  "job_id": "abc123"
}
```

Output:

```json
{
  "job_id": "abc123",
  "status": "FAILED",
  "created_at": "...",
  "started_at": "...",
  "completed_at": "...",
  "error_type": "KeyError",
  "error_message": "price"
}
```

---

## `get_job_logs`

Input:

```json
{
  "job_id": "abc123"
}
```

Output:

```json
{
  "entries": [
    {
      "timestamp": "...",
      "level": "ERROR",
      "message": "Required column not found"
    }
  ]
}
```

---

## `get_job_metrics`

Input:

```json
{
  "job_id": "abc123",
  "window_minutes": 10
}
```

Output may include:

```json
{
  "worker_duration_seconds": 1.8,
  "memory_usage_mb": 420,
  "queue_wait_seconds": 0.4
}
```

---

## `get_job_trace`

Input:

```json
{
  "job_id": "abc123"
}
```

Output:

```json
{
  "trace_id": "xyz456",
  "failed_span": "transform_dataset",
  "duration_ms": 840,
  "error": "KeyError: price"
}
```

---

# 36. Agent Security

The agent should initially be read-only.

It should not have tools such as:

```text
restart_worker()
delete_database_record()
rerun_everything()
terminate_container()
change_configuration()
```

without strong controls.

Initial tools should focus on investigation.

This keeps the agent safe and predictable.

---

# 37. Human-in-the-Loop Direction

Later, if remediation actions are introduced, the architecture should separate recommendation from execution.

Example:

```text
Agent:
"I recommend retrying the worker."

        ↓

User approval required

        ↓

Deterministic backend executes retry
```

The model should not directly execute high-impact infrastructure changes without an approval mechanism.

---

# 38. Agent Observability

The AI layer itself should be observable.

Recommended metrics:

```text
agent_requests_total
agent_failures_total
agent_tool_calls_total
agent_tool_failures_total
agent_latency_seconds
```

Additional metadata may include:

```text
model
tool_name
job_id
trace_id
```

---

# 39. Agent Tracing

An investigation should produce spans such as:

```text
agent.investigation
    ↓
agent.tool.get_job
    ↓
agent.tool.get_logs
    ↓
agent.tool.get_metrics
    ↓
agent.tool.get_trace
    ↓
agent.generate_diagnosis
```

This allows debugging the agent itself.

---

# 40. LLM Provider Strategy

The architecture should avoid unnecessary dependency on one provider.

The application should ideally wrap LLM calls through an abstraction.

Conceptually:

```python
class LLMClient:
    def generate(...)
    def invoke_tools(...)
```

This allows development with:

- Ollama
- open-source models
- hosted inference providers
- Bedrock
- other compatible APIs

The business logic should not depend heavily on one vendor-specific SDK.

---

# 41. Local AI Development

For local development, Ollama can be used.

This provides:

- no dependency on paid credits
- easy local testing
- model experimentation
- private development

The agent implementation should remain flexible enough to later move to AWS-hosted or managed inference.

---

# 42. LangGraph Direction

LangGraph should not be introduced immediately unless the workflow actually requires it.

A simple first version can use:

```text
FastAPI
↓
Agent service
↓
LLM
↓
Tools
```

LangGraph becomes useful once workflows require:

- branching
- persistent state
- retries
- loops
- multiple decision steps
- human approval
- resumability
- multi-agent coordination

Example future graph:

```text
Start
  ↓
Fetch Job
  ↓
Check Failure Type
  ├─ application error → inspect logs
  ├─ infrastructure error → inspect metrics
  └─ unknown → inspect trace
  ↓
Correlate Evidence
  ↓
Generate Diagnosis
  ↓
Human Review
  ↓
Optional Action
```

---

# 43. Multi-Agent Direction

Do not begin with multiple agents.

Potential future specialized agents could include:

```text
Failure Investigator Agent
Performance Analysis Agent
Security Analysis Agent
Data Quality Agent
Cost Optimization Agent
Deployment Investigator Agent
```

However, these should only be introduced after one agent works reliably.

The presence of multiple agents is not itself an architectural advantage.

---

# 44. AI Platform Direction

The long-term platform architecture may eventually look like:

```text
                         Frontend
                            │
                            ▼
                         FastAPI
                            │
          ┌─────────────────┼───────────────────────┐
          │                 │                       │
          ▼                 ▼                       ▼
      Job APIs        Agent APIs              Status APIs
          │                 │
          ▼                 ▼
       Queue          Agent Orchestrator
          │                 │
          ▼                 ▼
       Workers         Tool Layer
          │        ┌────────┼────────┬────────┐
          │        ▼        ▼        ▼        ▼
          │       DB      Logs    Metrics   Traces
          │
          ▼
     Processing
```

This design keeps traditional workload processing and AI reasoning separated but connected.

---

# 45. Agentic Replacement Strategy

The existing backend should not be completely replaced by an agentic backend.

Instead:

```text
Traditional Backend
        +
Agentic Capability
```

The existing platform remains responsible for deterministic work.

The AI layer is introduced as another service capability.

For example:

```text
POST /jobs
GET /jobs/{id}
POST /agents/investigate-job
```

This is preferable to routing every backend operation through an LLM.

---

# 46. Production Agent Architecture on AWS

A future cloud version may look like:

```text
User
 │
 ▼
API Gateway / ALB
 │
 ▼
FastAPI on ECS
 │
 ├───────────── Traditional job APIs
 │
 └───────────── Agent API
                     │
                     ▼
                 Agent Service
                     │
                     ▼
             Model Provider / Bedrock
                     │
                     ▼
                  Tool Layer
        ┌────────────┼─────────────┐
        ▼            ▼             ▼
       RDS       CloudWatch        ECS
        │
        ▼
       S3
```

---

# 47. Tool Layer in AWS

The tool abstraction can map to managed AWS systems.

Examples:

```text
get_job()
    ↓
RDS PostgreSQL
```

```text
get_job_logs()
    ↓
CloudWatch Logs Insights
```

```text
get_job_metrics()
    ↓
CloudWatch Metrics / Prometheus
```

```text
get_job_trace()
    ↓
OpenTelemetry backend
```

```text
get_task_status()
    ↓
ECS API
```

```text
get_result_metadata()
    ↓
S3
```

---

# 48. Model Hosting Direction

Possible production approaches include:

- Amazon Bedrock
- hosted inference providers
- self-hosted model containers
- SageMaker
- external model APIs

The choice should depend on:

- cost
- latency
- security
- model quality
- operational burden
- customer requirements

---

# 49. Security Architecture

Security should be introduced gradually but should remain part of the design.

Key areas include:

- authentication
- authorization
- secrets management
- database permissions
- network segmentation
- IAM
- least privilege
- secure container configuration
- restricted agent tools

---

# 50. Authentication

Future API authentication may use:

```text
JWT
OAuth 2.0 / OIDC
Cognito
enterprise identity providers
```

The frontend should not directly access internal infrastructure services.

It should communicate through authenticated application APIs.

---

# 51. Authorization

Authorization should control:

- who can submit jobs
- who can inspect a job
- who can retrieve results
- who can run agent investigations
- who can approve remediation actions

Future multi-user designs should avoid allowing one user to inspect another user's jobs.

---

# 52. Secrets

Secrets must never be committed directly to the repository.

Examples:

```text
database passwords
API keys
LLM credentials
AWS credentials
```

Local development may use:

```text
.env
```

but `.env` files containing secrets should be ignored by Git.

Cloud deployment should use:

- AWS Secrets Manager
- Systems Manager Parameter Store

---

# 53. IAM

AWS services should use least-privilege IAM roles.

Examples:

The API task should only have access to resources it actually needs.

The worker task may need:

```text
S3 read/write
CloudWatch logging
specific database connectivity
```

The agent may need read-only access to:

```text
CloudWatch Logs
CloudWatch Metrics
job metadata
```

It should not automatically receive infrastructure administration permissions.

---

# 54. Networking

A production AWS environment should likely use a VPC.

Possible layout:

```text
Public Subnets
   │
   └── Load Balancer

Private Subnets
   ├── FastAPI ECS Tasks
   ├── Worker ECS Tasks
   ├── RDS
   └── ElastiCache
```

The database and Redis should not be publicly accessible.

---

# 55. Scalability

The architecture should support independent scaling.

## API scaling

Scale based on:

- request count
- CPU
- memory
- latency

---

## Worker scaling

Worker scaling may be based on:

- queue depth
- pending jobs
- CPU
- processing duration

---

## Database scaling

RDS can later introduce:

- larger instance classes
- read replicas
- connection pooling

if needed.

---

# 56. Large Job Processing

If job workloads become very heavy, long-lived RQ workers may no longer be the best model.

Alternative architecture:

```text
Job submitted
    ↓
Queue
    ↓
Launch dedicated ECS task
    ↓
Process job
    ↓
Task exits
```

This isolates workloads and can improve scalability.

---

# 57. AWS Batch Direction

For extremely large or compute-intensive processing jobs, AWS Batch could become relevant.

Possible use cases:

- long-running data transformations
- large dataset analysis
- ML processing workloads
- high-throughput batch computation

AWS Batch should only be introduced if workloads justify it.

---

# 58. Step Functions Distributed Map Direction

If one uploaded dataset needs to be split into many parallel processing units, a future pattern could be:

```text
Upload dataset
     ↓
Split into partitions
     ↓
Step Functions Distributed Map
     ↓
many ECS/Lambda tasks
     ↓
aggregate results
```

This is relevant for large-scale parallel workloads.

---

# 59. Storage Direction

The current application may process files locally.

The cloud-native architecture should move durable file storage to S3.

Potential paths:

```text
uploads/{job_id}/input.csv
results/{job_id}/result.csv
```

Advantages:

- durable storage
- independent from container lifecycle
- scalable
- low cost
- easy integration with event-driven systems

---

# 60. Presigned Upload Direction

Instead of uploading very large files through FastAPI, the future architecture may use:

```text
Frontend
   ↓
Request presigned URL
   ↓
FastAPI
   ↓
Generate presigned S3 URL
   ↓
Frontend uploads directly to S3
```

Then:

```text
S3 upload complete
   ↓
job created / event emitted
   ↓
processing starts
```

This removes large file transfer load from the API.

---

# 61. Event-Driven Upload Processing

A later pattern may look like:

```text
Frontend
    ↓
S3 Upload
    ↓
S3 Event
    ↓
EventBridge
    ↓
SQS
    ↓
Worker
```

or:

```text
S3
 ↓
EventBridge
 ↓
Step Functions
 ↓
ECS Tasks
```

The exact design depends on workflow complexity.

---

# 62. Frontend Evolution

The frontend may evolve from a basic upload page into a small operations console.

Possible screens:

```text
Upload
Jobs
Job Details
Metrics
Failure Investigation
System Status
```

A Job Details screen could show:

```text
job status
created time
processing duration
result
failure reason
trace link
investigate failure button
```

---

# 63. Failure Investigation UX

For failed jobs:

```text
Job FAILED
   ↓
[Investigate Failure]
   ↓
Agent gathers evidence
   ↓
UI displays:

Summary
Likely cause
Evidence
Suggested fix
Confidence
```

This creates a meaningful end-to-end agentic use case.

---

# 64. Data Quality Evolution

The original CSV-processing system can later evolve into more advanced data-quality workflows.

Examples:

- missing-value detection
- schema validation
- duplicate detection
- type consistency
- outlier detection
- quality scoring
- automated recommendations

An agent could eventually interpret quality findings.

For example:

```text
"Why is this dataset considered low quality?"
```

The agent could reason over deterministic quality metrics rather than generating unsupported conclusions.

---

# 65. Agentic Data Analysis Direction

A later feature could allow natural-language questions about processed datasets.

Possible flow:

```text
User question
    ↓
Agent
    ↓
Dataset metadata tool
    ↓
Query tool
    ↓
Statistical tool
    ↓
LLM explanation
```

The system should avoid giving the model unrestricted arbitrary SQL access.

Prefer controlled query interfaces.

---

# 66. Platform API Boundaries

The architecture should maintain clear domain boundaries.

Possible modules:

```text
api/
jobs/
workers/
processing/
database/
observability/
agents/
agent_tools/
infrastructure/
```

The exact folder structure should follow the real repository, but conceptual boundaries should remain clear.

---

# 67. Agent Module Boundary

Agent code should remain separate from worker logic.

Example conceptual structure:

```text
backend/
├── api/
├── jobs/
├── workers/
├── processing/
├── observability/
├── agents/
│   ├── failure_investigator.py
│   └── prompts.py
└── agent_tools/
    ├── job_tool.py
    ├── logs_tool.py
    ├── metrics_tool.py
    └── trace_tool.py
```

Codex should inspect the actual repository before creating directories or moving files.

---

# 68. Deterministic vs AI Responsibilities

The architecture should clearly divide responsibilities.

## Deterministic code

Responsible for:

- validation
- queueing
- retries
- persistence
- authentication
- authorization
- job state changes
- deployment
- infrastructure control
- file handling
- metrics

## AI

Responsible for:

- explaining failures
- correlating evidence
- generating summaries
- interpreting patterns
- suggesting remediation
- answering natural-language operational questions

This boundary is important.

---

# 69. Error Handling Philosophy

Every major component should fail clearly.

Bad failure:

```text
500 Internal Server Error
```

with no useful information anywhere.

Better failure:

```text
API returns safe error
job is marked FAILED
exception is logged
trace marks span as error
failure metric increments
database contains failure metadata
```

This creates operational visibility.

---

# 70. Graceful Startup

Docker Compose services should not assume dependencies are immediately ready.

For example:

```text
API starts
↓
Postgres still starting
↓
API crashes permanently
```

should be avoided.

Use:

- health checks
- readiness logic
- startup retries
- dependency checks

where appropriate.

---

# 71. Graceful Shutdown

Workers should ideally complete or safely release active jobs before shutting down.

The architecture should avoid corrupting job state during deployments.

---

# 72. Deployment Reliability

Deployment should ideally evolve toward:

```text
build
↓
deploy
↓
health check
↓
smoke test
↓
mark successful
```

If health verification fails:

```text
deployment should fail visibly
```

Future cloud deployments may support automatic rollback.

---

# 73. Configuration Management

Configuration should be externalized.

Examples:

```text
DATABASE_URL
REDIS_URL
OTEL_EXPORTER_OTLP_ENDPOINT
ENVIRONMENT
LOG_LEVEL
LLM_PROVIDER
LLM_MODEL
```

Do not hard-code environment-specific values inside application logic.

---

# 74. Environment Separation

Eventually the system should support:

```text
development
staging
production
```

These environments should differ through configuration, not different codebases.

Terraform configuration may use:

```text
modules
environment variables
tfvars
workspaces
```

depending on the final infrastructure strategy.

---

# 75. Cost Awareness

Cloud architecture choices should consider cost.

For example:

A continuously running ECS service is appropriate for APIs.

A task-per-job approach may make more sense for sporadic heavy workloads.

A Lambda may be cheaper for small, short-lived operations.

Architecture choices should be workload-driven rather than service-driven.

---

# 76. Portfolio Value

The purpose of this platform is also to demonstrate architecture capability.

It should show evidence of practical understanding of:

```text
REST APIs
asynchronous jobs
distributed systems
queues
containers
CI/CD
monitoring
tracing
databases
cloud infrastructure
AWS
Terraform
agentic AI
LLM tool use
production reliability
```

The project should therefore emphasize architecture reasoning and operational behavior rather than simply adding UI features.

---

# 77. Target Skill Demonstration

The completed project should support discussions for roles including:

- Cloud Engineer
- Platform Engineer
- Cloud Platform Engineer
- Data & Cloud Engineer
- Cloud-Native Engineer
- Solutions Architect
- Cloud Solutions Architect
- AI Platform Engineer
- Agentic Platform Engineer

The project should demonstrate not only knowledge of individual AWS services but the ability to explain:

- why a service was selected
- what problem it solves
- alternatives
- tradeoffs
- scaling behavior
- failure behavior
- operational implications

---

# 78. Development Roadmap

The project should evolve in the following general order.

## Phase 1 — Stable application

Ensure the current application works reliably.

Components:

- React
- FastAPI
- PostgreSQL
- Redis
- RQ
- Pandas
- Docker Compose

Goals:

- correct upload behavior
- reliable job state
- correct results
- clear errors

---

## Phase 2 — Automated testing

Add or improve:

- backend unit tests
- API integration tests
- worker tests
- invalid upload tests
- frontend validation

Goal:

Develop confidence that changes do not break the application.

---

## Phase 3 — CI/CD

Strengthen GitHub Actions.

Goals:

```text
test
build
deploy
verify
```

Use the self-hosted runner to simulate deployment automation.

---

## Phase 4 — Observability

Improve:

- metrics
- traces
- structured logs
- dashboards
- job correlation

Goals:

Understand application behavior without manually reading random logs.

---

## Phase 5 — Reliability

Add:

- bounded retries
- idempotency
- timeouts
- failed-job persistence
- readiness checks
- graceful behavior

Goal:

Handle failures intentionally.

---

## Phase 6 — Infrastructure as Code

Introduce Terraform.

Goals:

- reproducible infrastructure
- version-controlled infrastructure
- AWS learning
- environment portability

---

## Phase 7 — AWS architecture

Move major components toward:

```text
ECS
ECR
RDS
ElastiCache
S3
CloudWatch
IAM
VPC
Terraform
```

Goal:

Demonstrate a production cloud architecture.

---

## Phase 8 — Agentic operations

Implement the first agent:

```text
Job Failure Investigator
```

Goals:

- tool calling
- operational evidence retrieval
- agent reasoning
- AI observability
- safe read-only tools

---

## Phase 9 — Agent observability

Add:

- agent metrics
- traces
- tool-call telemetry
- model usage metrics
- error monitoring

Goal:

Treat AI as an observable production subsystem.

---

## Phase 10 — Advanced workflow orchestration

Only when justified, introduce:

- LangGraph
- Step Functions
- EventBridge
- SNS
- SQS
- multiple agents
- human approval workflows

---

# 79. Example Final Architecture

A mature version of the project may eventually resemble:

```text
                              ┌──────────────────────┐
                              │      Frontend        │
                              │  React / TypeScript  │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ API Gateway / ALB    │
                              └──────────┬───────────┘
                                         │
                                         ▼
                              ┌──────────────────────┐
                              │ FastAPI on ECS       │
                              │ Fargate              │
                              └───────┬───────┬──────┘
                                      │       │
                                      │       │
                           ┌──────────┘       └──────────────┐
                           ▼                                 ▼
                  ┌─────────────────┐                ┌─────────────────┐
                  │ Traditional Job │                │ Agent Service   │
                  │ APIs            │                │                 │
                  └────────┬────────┘                └────────┬────────┘
                           │                                  │
                           ▼                                  ▼
                    Queue / SQS                         LLM / Bedrock
                           │                                  │
                           ▼                                  ▼
                    ECS Workers                         Agent Tools
                           │                        ┌─────────┼──────────┐
                           ▼                        ▼         ▼          ▼
                       Processing                  RDS      Logs     Metrics
                           │                                  │
                           ▼                                  ▼
                          S3                              CloudWatch
                           │
                           ▼
                      Job Results

                           Shared Platform Services

             ┌──────────────────────────────────────────────┐
             │ PostgreSQL / RDS                            │
             │ Redis / ElastiCache                         │
             │ OpenTelemetry                               │
             │ CloudWatch                                  │
             │ IAM                                         │
             │ VPC                                         │
             │ Terraform                                   │
             │ GitHub Actions                              │
             └──────────────────────────────────────────────┘
```

---

# 80. Architectural End State

The final project should demonstrate a clear progression:

```text
Simple Data Processing Application
        ↓
Asynchronous Job Platform
        ↓
Observable Distributed Application
        ↓
Reliable Production-Oriented Platform
        ↓
Infrastructure-as-Code Deployment
        ↓
AWS Cloud-Native Platform
        ↓
AI-Assisted Operations Platform
        ↓
Controlled Agentic Architecture
```

The point is not to maximize the number of technologies.

The point is to demonstrate the ability to identify a system requirement and choose the correct architectural pattern.

---

# 81. Key Architectural Rules for Future Development

Any future changes should respect the following rules:

1. Do not perform long-running work inside HTTP request handlers.
2. Preserve asynchronous processing.
3. Persist important job state.
4. Do not hide failures.
5. Keep retry behavior bounded.
6. Maintain health and readiness checks.
7. Keep observability intact.
8. Instrument new services and workflows.
9. Preserve Docker Compose compatibility during local development.
10. Keep cloud migration in mind when adding local-only components.
11. Use infrastructure as code for cloud resources.
12. Apply least-privilege security.
13. Do not give AI unrestricted infrastructure control.
14. AI should use explicit tools.
15. Tool access should be narrow and auditable.
16. Start with one useful agent before adding more agents.
17. Prefer deterministic workflows when deterministic behavior is sufficient.
18. Use Step Functions when explicit workflow orchestration is actually needed.
19. Use EventBridge for events, SQS for queues, SNS for fan-out where appropriate.
20. Avoid architecture complexity that cannot be explained by a real requirement.
21. Add tests whenever behavior changes.
22. Preserve backward compatibility where practical.
23. Keep service boundaries understandable.
24. Prefer incremental refactoring over large rewrites.
25. Treat operational reliability as a feature of the application.

---

# 82. Architectural Vision

The architectural vision for the project is:

```text
A cloud-native data-processing platform
that accepts asynchronous workloads,
executes them reliably,
makes their behavior observable,
deploys through automated pipelines,
runs on reproducible infrastructure,
and uses AI agents to understand and assist
with operational problems without replacing
deterministic application logic.
```

This is the central architectural direction for the repository.

Codex should use this document as architectural context when proposing or implementing substantial changes.