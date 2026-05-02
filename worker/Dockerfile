FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for opencv + deepface (libGL, libglib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Pre-download DeepFace model weights at build time to avoid cold-start delays
RUN python -c "from deepface import DeepFace; DeepFace.build_model('Facenet512')" || true

CMD ["celery", "-A", "src.celery_app.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
