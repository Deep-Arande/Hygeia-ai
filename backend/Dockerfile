# Used for the Railway deploy (and optional local prod-parity via docker compose).
# One image serves the API and, later, the Celery worker/beat — differing only in start command.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Railway overrides this for the worker/beat processes in Phase 5.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
