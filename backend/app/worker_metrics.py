from prometheus_client import Counter, Histogram

JOBS_COMPLETED_TOTAL = Counter(
    "data_quality_jobs_completed_total",
    "Total number of successfully completed CSV jobs",
)

JOBS_FAILED_TOTAL = Counter(
    "data_quality_jobs_failed_total",
    "Total number of failed CSV jobs",
)

JOB_PROCESSING_DURATION_SECONDS = Histogram(
    "data_quality_job_processing_duration_seconds",
    "Time spent processing CSV jobs",
)
