# EmailPilot App - Unified Calendar and Authentication System
# Multi-stage build: Frontend (Node.js) + Backend (Python)

# Stage 1: Build React Frontend with Vite
FROM node:18-alpine AS frontend-builder

WORKDIR /frontend

# Accept build argument for Clerk key (must be available at build time for Vite)
ARG VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy frontend source code and config files
COPY frontend/ ./
COPY vite.config.js* ./
COPY index.html* ./

# Build the React app with Vite
RUN npm run build

# Stage 2: Python Backend with Built Frontend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built frontend from Stage 1
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Set environment variables
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; import os; requests.get(f'http://localhost:{os.getenv(\"PORT\", 8080)}/health', timeout=5)"

# Run the unified FastAPI application
CMD sh -c "python -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --timeout-keep-alive 1200"
