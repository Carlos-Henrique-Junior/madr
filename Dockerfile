FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY madr ./madr

RUN pip install --no-cache-dir .

COPY alembic.ini ./
COPY migrations ./migrations

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && uvicorn madr.app:app --host 0.0.0.0 --port 8000"]
