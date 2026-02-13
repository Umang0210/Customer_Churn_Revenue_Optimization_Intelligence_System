# -----------------------------
# Base Image
# -----------------------------
FROM python:3.10-slim

# -----------------------------
# Environment Variables
# -----------------------------
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV CI_MODE=true

# -----------------------------
# Working Directory
# -----------------------------
WORKDIR /app

# -----------------------------
# System Dependencies
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------
# Install Python Dependencies
# -----------------------------
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# Copy Application Code
# -----------------------------
COPY api/ api/
COPY models/ models/

# -----------------------------
# Expose Port
# -----------------------------
EXPOSE 8000

# -----------------------------
# Start FastAPI
# -----------------------------
CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
