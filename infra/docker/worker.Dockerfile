FROM python:3.11-slim

WORKDIR /app

COPY apps/api/pyproject.toml /app/pyproject.toml
COPY apps/api /app

RUN pip install --no-cache-dir .

CMD ["python", "-m", "app.workers.queue"]
