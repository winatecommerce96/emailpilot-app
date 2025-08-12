#!/bin/bash

# Initialize database with Alembic
echo "Initializing database..."
python -c "
from app.core.database import Base, engine
Base.metadata.create_all(bind=engine)
print('Database tables created successfully')
"

# Start the application
echo "Starting EmailPilot API..."
uvicorn main:app --host 0.0.0.0 --port 8080