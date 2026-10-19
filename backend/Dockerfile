FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    YF_DISABLE_CURL_CFFI=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Champion LightGBM inference imports repo-root `ml/` (see backend/inference.py).
COPY ml /app/ml
COPY backend /app/backend
ENV PYTHONPATH=/app:/app/backend
WORKDIR /app/backend

EXPOSE 8000
# Render (and others) set PORT; default 8000 for local Docker Compose.
CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
