# Firebase Setup Guide for EmailPilot.ai

This guide walks through setting up Firebase as the primary database for EmailPilot.ai, providing scalable and robust data storage across all projects.

## 🏗️ Architecture Overview

### **Firebase Firestore Collections**
```
emailpilot-database/
├── clients/                    # Client management
│   └── {clientId}/
│       ├── name: string
│       ├── metric_id: string
│       ├── api_key_encrypted: string
│       ├── is_active: boolean
│       ├── created_at: timestamp
│       └── updated_at: timestamp
│
├── calendar_events/           # Calendar functionality
│   └── {eventId}/
│       ├── client_id: string (ref)
│       ├── title: string
│       ├── content: string
│       ├── event_date: string (YYYY-MM-DD)
│       ├── event_type: string
│       ├── color: string
│       ├── segment: string
│       ├── send_time: string
│       ├── subject_a: string
│       ├── subject_b: string
│       ├── preview_text: string
│       ├── main_cta: string
│       ├── offer: string
│       ├── ab_test: string
│       ├── imported_from_doc: boolean
│       ├── import_doc_id: string
│       ├── created_at: timestamp
│       └── updated_at: timestamp
│
├── calendar_chat_history/     # AI Chat logs
│   └── {chatId}/
│       ├── client_id: string (ref)
│       ├── user_message: string
│       ├── ai_response: string
│       ├── is_action: boolean
│       ├── action_type: string
│       ├── session_id: string
│       └── created_at: timestamp
│
├── goals/                     # Revenue goals
│   └── {goalId}/
│       ├── client_id: string (ref)
│       ├── target_amount: number
│       ├── current_amount: number
│       ├── period: string
│       └── created_at: timestamp
│
├── reports/                   # Performance reports
│   └── {reportId}/
│       ├── client_id: string (ref)
│       ├── report_type: string
│       ├── data: map
│       ├── generated_at: timestamp
│       └── status: string
│
└── audit_logs/               # System audit logs
    └── {logId}/
        ├── user_id: string
        ├── action: string
        ├── resource: string
        ├── timestamp: timestamp
        └── metadata: map
```

## 🚀 Setup Instructions

### 1. Create Firebase Project

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login to Firebase
firebase login

# Create new project
firebase projects:create emailpilot-prod

# Initialize Firestore
firebase init firestore
```

### 2. Configure Security Rules

Create `firestore.rules`:
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Authentication required for all operations
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // Client-specific data access
    match /calendar_events/{eventId} {
      allow read, write: if request.auth != null 
        && resource.data.client_id in request.auth.token.client_access;
    }
    
    match /clients/{clientId} {
      allow read, write: if request.auth != null 
        && clientId in request.auth.token.client_access;
    }
  }
}
```

### 3. Environment Configuration

Create `.env` file:
```bash
# Firebase Configuration
GOOGLE_CLOUD_PROJECT=emailpilot-prod
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Gemini AI
GEMINI_API_KEY=your_gemini_api_key_here

# JWT Authentication
SECRET_KEY=your-super-secret-jwt-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Environment
ENVIRONMENT=production
DEBUG=false
```

### 4. Service Account Setup

```bash
# Create service account
gcloud iam service-accounts create emailpilot-service \
    --display-name="EmailPilot Service Account"

# Grant Firestore permissions
gcloud projects add-iam-policy-binding emailpilot-prod \
    --member="serviceAccount:emailpilot-service@emailpilot-prod.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

# Create and download key
gcloud iam service-accounts keys create emailpilot-service-account.json \
    --iam-account=emailpilot-service@emailpilot-prod.iam.gserviceaccount.com
```

### 5. Update Requirements

Add Firebase dependencies to `requirements.txt`:
```
firebase-admin>=6.2.0
google-cloud-firestore>=2.11.0
google-cloud-storage>=2.10.0
```

## 📊 Firebase vs BigQuery Decision

### **Firebase Firestore** ✅ (Recommended for EmailPilot)
- **Real-time updates** - Perfect for calendar drag-drop
- **ACID transactions** - Data consistency
- **Auto-scaling** - Handles traffic spikes
- **Offline support** - Works with poor connectivity
- **Simple queries** - Great for CRUD operations
- **Cost-effective** - Pay per operation

### **BigQuery** (For Analytics Later)
- **Complex analytics** - Use for reporting
- **Large datasets** - Historical data analysis
- **SQL queries** - Familiar query language
- **Data warehouse** - Separate from operational data

### **Hybrid Approach** 🎯
- **Firestore** → Operational data (clients, calendar, chat)
- **BigQuery** → Analytics data (reports, metrics, trends)
- **Data Pipeline** → Stream Firestore → BigQuery for analysis

## 🔧 Migration Strategy

### Phase 1: Calendar Migration (Current)
```bash
# Deploy Firebase calendar
python firebase_calendar_migration.py

# Test calendar functionality
python test_firebase_calendar.py

# Update frontend to use Firebase endpoints
# Update API routes to /api/firebase-calendar/*
```

### Phase 2: Client Data Migration
```bash
# Migrate existing client data to Firebase
python migrate_clients_to_firebase.py

# Update all client endpoints
# Test client management functionality
```

### Phase 3: Full Platform Migration
```bash
# Migrate goals, reports, audit logs
python migrate_remaining_data.py

# Remove SQLAlchemy dependencies
# Update all API endpoints
# Deploy to production
```

## 🔒 Security Configuration

### Firestore Security Rules
```javascript
// Advanced security rules
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // User authentication required
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // Role-based access control
    match /clients/{clientId} {
      allow read: if request.auth.token.role in ['admin', 'user'];
      allow write: if request.auth.token.role == 'admin';
    }
    
    // Client-scoped data access
    match /calendar_events/{eventId} {
      allow read, write: if request.auth != null 
        && (request.auth.token.role == 'admin' 
        || resource.data.client_id in request.auth.token.client_access);
    }
  }
}
```

### Authentication Integration
```python
# Custom token generation for Firebase
import firebase_admin
from firebase_admin import auth

def create_custom_token(user_data):
    additional_claims = {
        'role': user_data['role'],
        'client_access': user_data['client_ids']
    }
    
    custom_token = auth.create_custom_token(
        uid=user_data['id'],
        additional_claims=additional_claims
    )
    
    return custom_token
```

## 📈 Monitoring & Analytics

### Firestore Monitoring
```bash
# Enable monitoring
gcloud logging sinks create emailpilot-firestore-logs \
    bigquery.googleapis.com/projects/emailpilot-prod/datasets/firestore_logs

# Create alerts
gcloud alpha monitoring policies create firestore-errors.yaml
```

### Performance Optimization
- **Composite indexes** for complex queries
- **Connection pooling** for high traffic
- **Caching layer** with Redis for frequent reads
- **Batch operations** for bulk updates

## 🚀 Deployment Commands

```bash
# 1. Deploy Firestore rules
firebase deploy --only firestore:rules

# 2. Deploy indexes
firebase deploy --only firestore:indexes

# 3. Deploy Cloud Functions (if using)
firebase deploy --only functions

# 4. Start EmailPilot with Firebase
export GOOGLE_APPLICATION_CREDENTIALS=./emailpilot-service-account.json
uvicorn main:app --host 0.0.0.0 --port 8080
```

## 🔄 Data Migration Script

Create `migrate_to_firebase.py`:
```python
#!/usr/bin/env python3
"""
Migrate existing EmailPilot data to Firebase Firestore
"""

import asyncio
from firebase_calendar_integration import firebase_clients, firebase_calendar
from app.core.database import engine
from sqlalchemy.orm import sessionmaker
from app.models.client import Client as SQLClient

async def migrate_clients():
    """Migrate clients from SQL to Firebase"""
    # Get SQL data
    Session = sessionmaker(bind=engine)
    session = Session()
    
    sql_clients = session.query(SQLClient).all()
    
    for sql_client in sql_clients:
        # Convert to Firebase format
        firebase_data = {
            'name': sql_client.name,
            'metric_id': sql_client.metric_id,
            'is_active': sql_client.is_active,
            'api_key_encrypted': sql_client.api_key_encrypted
        }
        
        # Create in Firebase
        firebase_id = await firebase_clients.create_client(firebase_data)
        print(f"Migrated client: {sql_client.name} -> {firebase_id}")
    
    session.close()

if __name__ == "__main__":
    asyncio.run(migrate_clients())
```

## ✅ Benefits of Firebase Implementation

### **Scalability**
- Auto-scales to millions of operations
- No server management required
- Global CDN for fast access

### **Reliability** 
- 99.999% uptime SLA
- Automatic backups
- Multi-region replication

### **Developer Experience**
- Real-time listeners for UI updates
- Offline-first architecture
- Simple SDK integration

### **Cost Optimization**
- Pay per operation model
- Free tier covers development
- Predictable pricing structure

### **Security**
- Built-in authentication
- Granular security rules
- Encryption at rest and in transit

This Firebase implementation provides a robust, scalable foundation for EmailPilot.ai that can grow with your business needs!