FROM python:3.11-slim  #Base image with Python 3.11     

ENV PYTHONDONTWRITEBYTECODE=1  
ENV PYTHONUNBUFFERED=1

WORKDIR /app     # Set working directory

COPY requirements.txt .        
RUN pip install --no-cache-dir -r requirements.txt      

COPY api/ api/ 
COPY models/ models/
COPY src/ src/

EXPOSE 8000  

CMD ["uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]  