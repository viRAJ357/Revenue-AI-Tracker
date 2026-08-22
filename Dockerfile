FROM python:3.11-slim

# Prevents Python from writing .pyc files and enables output buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=7860

WORKDIR /app

# Install system dependencies (libgomp1 is required by CatBoost)
RUN apt-get update && apt-get install -y libgomp1 && rm -rf /var/lib/apt/lists/*

# Install python dependencies first (better Docker layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source, frontend, and the trained ML model
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY model/ ./model/

# Make the backend directory writable so SQLite can create journal files when running as non-root on Render
RUN chmod -R 777 /app/backend

WORKDIR /app/backend

# Render sets the PORT env variable automatically. We use shell form to interpolate it.
CMD gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers 2 \
    --bind 0.0.0.0:$PORT \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
