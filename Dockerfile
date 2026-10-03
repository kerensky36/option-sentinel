FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY frontend/ ./frontend/

# Run as an unprivileged user (specs/022 FR-511); the app only reads its files.
RUN useradd --system --no-create-home --uid 10001 app
USER app

# Expose Cloud Run port
EXPOSE 8080

# Run with access logging disabled to prevent any token values appearing in logs.
# Cloud Run structured logging is used instead.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
