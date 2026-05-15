FROM python:3.13-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/ ./src/
COPY frontend/ ./frontend/

# Expose Cloud Run port
EXPOSE 8080

# Run with access logging disabled to prevent any token values appearing in logs.
# Cloud Run structured logging is used instead.
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log"]
