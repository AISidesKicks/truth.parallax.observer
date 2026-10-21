# parallax.observer App Container
# Lightweight image for the main application.
# Talks to the llama.cpp services (prlx-llm:8080, prlx-embed:8080) and to
# the OpenViking context server (prlx-viking:1933).

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY docker/requirements-app.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

RUN mkdir -p /app/models \
    /app/data \
    /app/viking_data \
    /app/logs \
    /app/src

COPY src/ /app/src/
COPY scripts/ /app/scripts/
COPY config/ /app/config/

EXPOSE 8668

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8668/health || exit 1

CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8668"]
