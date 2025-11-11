FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for potential database connections
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements_firestore.txt .
RUN pip install --no-cache-dir -r requirements_firestore.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)"

CMD ["uvicorn", "main_firestore:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "300"]