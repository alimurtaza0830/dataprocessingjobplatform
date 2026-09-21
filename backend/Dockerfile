FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 appuser \
    && useradd --system --uid 10001 --gid appuser --home-dir /app appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser migrations ./migrations

RUN mkdir -p /data/uploads \
    && chown -R appuser:appuser /app /data/uploads

EXPOSE 8000

USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM base AS test

USER root

COPY --chown=appuser:appuser pytest.ini .
COPY --chown=appuser:appuser tests ./tests

USER appuser
