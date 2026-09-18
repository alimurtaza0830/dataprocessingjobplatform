from prometheus_client import start_http_server
from rq import SimpleWorker

from app.queue import processing_queue, redis_connection
from app.worker_tracing import configure_worker_tracing


def main() -> None:
    configure_worker_tracing()
    start_http_server(9101)

    worker = SimpleWorker(
        [processing_queue],
        connection=redis_connection,
    )

    worker.work()


if __name__ == "__main__":
    main()
