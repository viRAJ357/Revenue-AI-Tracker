FROM python:3.11-slim

# Prevents Python from writing .pyc files and enables output buffering
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (better Docker layer caching)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source and the trained ML model
COPY backend/ ./backend/
COPY model/ ./model/

WORKDIR /app/backend

EXPOSE 8000

# Use gunicorn with uvicorn workers for production concurrency.
# Override with CMD in docker-compose for celery worker.
CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "2", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
