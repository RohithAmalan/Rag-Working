from time import perf_counter

from prometheus_client import (CONTENT_TYPE_LATEST, Counter, Gauge, Histogram,
                               generate_latest)

HTTP_REQUESTS_TOTAL = Counter(
    "rag_http_requests_total",
    "Total HTTP requests handled by the API.",
    ["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "rag_http_request_duration_seconds",
    "Latency of HTTP requests in seconds.",
    ["method", "endpoint"],
)

RAG_QUERIES_TOTAL = Counter(
    "rag_queries_total",
    "Total number of RAG queries.",
    ["status", "workflow"],
)

RAG_QUERY_DURATION_SECONDS = Histogram(
    "rag_query_duration_seconds",
    "End-to-end RAG query duration in seconds.",
    ["workflow"],
    buckets=(0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0),
)

UPLOADS_TOTAL = Counter(
    "rag_uploads_total",
    "Total number of upload attempts.",
    ["status"],
)

UPLOADED_FILES_TOTAL = Counter(
    "rag_uploaded_files_total",
    "Total number of files uploaded.",
)

RETRIEVED_CHUNKS_HISTOGRAM = Histogram(
    "rag_retrieved_chunks_count",
    "Number of chunks retrieved per query.",
    buckets=(1, 3, 5, 8, 13, 21, 34),
)

STORAGE_BACKEND_INFO = Gauge(
    "rag_storage_backend_info",
    "Active storage backend label; value is always 1.",
    ["backend"],
)


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


def start_timer() -> float:
    return perf_counter()


def observe_http_request(
    method: str, endpoint: str, status_code: int, started: float
) -> None:
    duration = perf_counter() - started
    HTTP_REQUESTS_TOTAL.labels(
        method=method, endpoint=endpoint, status=str(status_code)
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, endpoint=endpoint).observe(
        duration
    )


def observe_rag_query(
    duration_seconds: float,
    status: str,
    workflow: str,
    retrieved_chunks: int | None = None,
) -> None:
    RAG_QUERIES_TOTAL.labels(status=status, workflow=workflow).inc()
    RAG_QUERY_DURATION_SECONDS.labels(workflow=workflow).observe(duration_seconds)
    if retrieved_chunks is not None:
        RETRIEVED_CHUNKS_HISTOGRAM.observe(max(retrieved_chunks, 0))


def observe_upload(status: str, files_count: int) -> None:
    UPLOADS_TOTAL.labels(status=status).inc()
    if files_count > 0:
        UPLOADED_FILES_TOTAL.inc(files_count)


def set_storage_backend(backend: str) -> None:
    STORAGE_BACKEND_INFO.labels(backend=backend).set(1)
