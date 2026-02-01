FROM python:3.11-slim  #Base image with Python 3.11     

ENV PYTHONDONTWRITEBYTECODE=1  #Environment hygiene
ENV PYTHONUNBUFFERED=1

WORKDIR /app     # Set working directory

COPY requirements.txt .        # Copy requirements file
RUN pip install --no-cache-dir -r requirements.txt      # Install dependencies

COPY api/ api/ # Copy FastAPI application
COPY models/ models/
COPY src/ src/

EXPOSE 8000  # Expose FastAPI port 

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]  # Start FastAPI
