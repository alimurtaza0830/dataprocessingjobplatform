from prometheus_client import Counter, Histogram

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
)

JOBS_UPLOADED_TOTAL = Counter(
    "data_quality_jobs_uploaded_total",
    "Total number of CSV processing jobs accepted",
)

UPLOAD_SIZE_BYTES = Histogram(
    "data_quality_upload_size_bytes",
    "Size of uploaded CSV files in bytes",
)