# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Camada de dependências isolada do código: rebuild só quando o pyproject muda.
COPY pyproject.toml README.md ./
RUN python - <<'PY'
import subprocess
import tomllib

deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']
subprocess.check_call(['pip', 'install', '--no-cache-dir', *deps])
PY

# O pacote em si entra depois e sem dependências (já instaladas acima).
COPY madr ./madr
RUN pip install --no-cache-dir --no-deps .

COPY alembic.ini ./
COPY migrations ./migrations

# Usuário sem privilégios: o processo não roda como root.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

# Migração antes de subir: o container nunca serve schema desatualizado.
# `exec` garante que o uvicorn receba SIGTERM e pare sem deixar órfãos.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn madr.app:app --host 0.0.0.0 --port 8000"]
