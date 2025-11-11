# EmailPilot App - Unified Calendar and Authentication System
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from emailpilot-app and install dependencies
COPY emailpilot-app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy emailpilot-app code
COPY emailpilot-app/ ./emailpilot-app/

# Copy emailpilot-simple code (needed for calendar tools, agents, and data modules)
COPY emailpilot-simple/ ./emailpilot-simple/

# Set environment variables - include both directories in Python path
ENV PYTHONPATH=/app/emailpilot-app:/app/emailpilot-simple
ENV PORT=8000

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)"

# Run the unified FastAPI application
CMD ["uvicorn", "emailpilot-app.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--timeout-keep-alive", "1200"]