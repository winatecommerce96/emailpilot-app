# Client Dropdown System Rebuild Guide

**Complete instructions for rebuilding the EmailPilot client dropdown functionality from scratch**

---

## 📋 Required Files Overview

### **Core Files (Required)**
1. **`app/api/admin_clients.py`** - Main API endpoints for client management
2. **`app/deps/firestore.py`** - Database connection setup
3. **`app/services/client_key_resolver.py`** - API key resolution service
4. **`app/services/secrets.py`** - Secret Manager integration
5. **`frontend/public/calendar_master.html`** - Frontend dropdown UI
6. **`main_firestore.py`** - Router mounting (modification needed)

### **Dependency Files**
1. **`app/deps/__init__.py`** - Dependency exports
2. **`app/core/settings.py`** - Configuration management
3. **`requirements.txt`** - Python dependencies

---

## 🗄️ Database Schema

### **Firestore Collection: `clients`**

```javascript
// Document ID: auto-generated or custom
{
  "id": "client-uuid-here",
  "name": "Client Company Name",
  "client_slug": "client-company-name",
  "is_active": true,
  "has_klaviyo_key": true,
  "klaviyo_api_key_secret": "klaviyo-api-key-client-name",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z",
  "contact_email": "contact@client.com",
  "industry": "E-commerce",
  "notes": "Additional client notes"
}
```

### **Required Fields for Dropdown**
- `id` (string) - Unique identifier
- `name` (string) - Display name for dropdown
- `client_slug` (string) - URL-safe identifier
- `is_active` (boolean) - Whether client should appear
- `has_klaviyo_key` (boolean) - Whether API key is configured

---

## 🔧 Backend Implementation

### **1. FastAPI Dependencies Setup**

**File: `app/deps/__init__.py`**
```python
from .firestore import get_db
from .secrets import get_secret_manager_service
from app.core.auth import get_current_user

__all__ = ["get_db", "get_secret_manager_service", "get_current_user"]
```

**File: `app/deps/firestore.py`**
```python
import os
import json
import logging
from google.cloud import firestore
from google.oauth2 import service_account
from app.services.secrets import SecretManagerService

logger = logging.getLogger(__name__)

_DB_CLIENT: firestore.Client | None = None

def get_db() -> firestore.Client:
    global _DB_CLIENT
    if _DB_CLIENT is not None:
        return _DB_CLIENT
    
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCLOUD_PROJECT")
    
    if not project_id:
        logger.error("No Google Cloud project ID found in environment")
        raise ValueError("GOOGLE_CLOUD_PROJECT environment variable must be set")
    
    # Try to get credentials from Secret Manager
    try:
        secret_manager = SecretManagerService(project_id=project_id)
        credentials_json = secret_manager.get_secret("firestore-service-account")
        if credentials_json:
            logger.info("Using Firestore credentials from Secret Manager")
            credentials_dict = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(
                credentials_dict,
                scopes=["https://www.googleapis.com/auth/datastore"]
            )
            _DB_CLIENT = firestore.Client(project=project_id, credentials=credentials)
            return _DB_CLIENT
    except Exception as e:
        logger.warning(f"Could not load credentials from Secret Manager: {e}")

    # Fallback to default credentials
    logger.info("Using Application Default Credentials for Firestore")
    _DB_CLIENT = firestore.Client(project=project_id)
    return _DB_CLIENT
```

### **2. Secret Manager Service**

**File: `app/services/secrets.py`**
```python
import os
import logging
from typing import Optional
from google.cloud import secretmanager
from google.oauth2 import service_account

logger = logging.getLogger(__name__)

class SecretNotFoundError(Exception):
    pass

class SecretManagerService:
    def __init__(self, project_id: Optional[str] = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        if not self.project_id:
            raise ValueError("Project ID must be provided or set in GOOGLE_CLOUD_PROJECT")
        
        try:
            self.client = secretmanager.SecretManagerServiceClient()
        except Exception as e:
            logger.error(f"Failed to initialize Secret Manager client: {e}")
            raise

    def get_secret(self, secret_name: str, version: str = "latest") -> Optional[str]:
        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            response = self.client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"Could not retrieve secret {secret_name}: {e}")
            return None
```

### **3. Client Key Resolver**

**File: `app/services/client_key_resolver.py`**
```python
import logging
import re
from typing import Optional, Dict, Any
from google.cloud import firestore
from fastapi import Depends
from app.deps.firestore import get_db
from app.services.secrets import SecretManagerService, SecretNotFoundError
from app.deps import get_secret_manager_service

logger = logging.getLogger(__name__)

class ClientKeyResolver:
    def __init__(self, db: firestore.Client, secret_manager: SecretManagerService):
        self.db = db
        self.secret_manager = secret_manager
        self._client_cache = {}

    def normalize_client_name(self, client_name: str) -> str:
        normalized = client_name.lower()
        normalized = re.sub(r'\b(llc|inc|corp|ltd|company|co\.?)\b', '', normalized)
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        normalized = re.sub(r'\s+', '-', normalized.strip())
        normalized = re.sub(r'-+', '-', normalized)
        normalized = normalized.strip('-')
        return normalized

    def generate_secret_name(self, client_name: str, client_id: str = None) -> str:
        normalized = self.normalize_client_name(client_name)
        return f"klaviyo-api-key-{normalized}"

    def get_client_api_key(self, client_id: str) -> Optional[str]:
        try:
            doc = self.db.collection("clients").document(client_id).get()
            if not doc.exists:
                return None
            
            client_data = doc.to_dict()
            secret_name = client_data.get("klaviyo_api_key_secret")
            
            if not secret_name:
                secret_name = self.generate_secret_name(client_data.get("name", ""))
            
            return self.secret_manager.get_secret(secret_name)
        except Exception as e:
            logger.error(f"Error getting API key for client {client_id}: {e}")
            return None

def get_client_key_resolver(
    db: firestore.Client = Depends(get_db),
    secret_manager: SecretManagerService = Depends(get_secret_manager_service)
) -> ClientKeyResolver:
    return ClientKeyResolver(db, secret_manager)
```

### **4. Main API Router**

**File: `app/api/admin_clients.py`**
```python
"""
Admin Client Management API
Comprehensive client data management for admin panel
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request, status, Depends
from pydantic import BaseModel
from google.cloud import firestore
from app.deps import get_db, get_secret_manager_service
from app.services.client_key_resolver import ClientKeyResolver, get_client_key_resolver

logger = logging.getLogger(__name__)

# All routes live under /api/admin/…
router = APIRouter(prefix="/api/admin", tags=["Admin Client Management"])

def get_current_user_from_session(request: Request):
    """Basic session check with dev bypass."""
    if os.getenv("ENVIRONMENT", "development") == "development":
        user = request.session.get("user")
        if not user:
            user = {"email": "admin@emailpilot.ai", "name": "Dev Admin"}
            request.session["user"] = user
        return user

    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

def generate_client_slug(name: str) -> str:
    """Generate a URL-safe client slug from the client name."""
    import re
    
    slug = name.lower().strip()
    slug = slug.replace("'", "").replace("&", "and")
    slug = re.sub(r'[\s\-]+', '-', slug)
    slug = re.sub(r'[^a-z0-9\-]', '', slug)
    slug = slug.strip('-')
    
    if not slug:
        slug = "client"
    
    return slug

class ClientCreate(BaseModel):
    name: str
    contact_email: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    has_klaviyo_key: Optional[bool] = None

@router.get("/clients")
async def get_all_clients(
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Get all clients with API key validation"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        docs = list(db.collection("clients").stream())
        clients: List[Dict[str, Any]] = []

        for d in docs:
            client_data = d.to_dict()
            client_data["id"] = d.id
            
            # Check if client has valid API key
            api_key = key_resolver.get_client_api_key(d.id)
            client_data["has_klaviyo_key"] = bool(api_key)
            
            clients.append(client_data)

        # Sort by name
        clients.sort(key=lambda x: x.get("name", "").lower())
        
        return {
            "clients": clients,
            "total": len(clients),
            "active_count": len([c for c in clients if c.get("is_active", False)]),
            "with_keys_count": len([c for c in clients if c.get("has_klaviyo_key", False)])
        }
    except Exception as e:
        logger.error(f"Error fetching clients: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch clients")

@router.get("/clients/{client_id}")
async def get_client_details(
    client_id: str, 
    request: Request, 
    key_resolver: ClientKeyResolver = Depends(get_client_key_resolver)
) -> Dict[str, Any]:
    """Get detailed information for a specific client"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc = db.collection("clients").document(client_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        client_data = doc.to_dict()
        client_data["id"] = doc.id
        
        # Check API key status
        api_key = key_resolver.get_client_api_key(client_id)
        client_data["has_klaviyo_key"] = bool(api_key)
        client_data["klaviyo_key_status"] = "valid" if api_key else "missing"
        
        return client_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch client details")

@router.post("/clients")
async def create_client(
    client_data: ClientCreate,
    request: Request
) -> Dict[str, Any]:
    """Create a new client"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        
        # Generate client slug
        client_slug = generate_client_slug(client_data.name)
        
        # Create client document
        new_client = {
            "name": client_data.name,
            "client_slug": client_slug,
            "contact_email": client_data.contact_email,
            "industry": client_data.industry,
            "notes": client_data.notes,
            "is_active": True,
            "has_klaviyo_key": False,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Add to Firestore
        doc_ref = db.collection("clients").add(new_client)
        client_id = doc_ref[1].id
        
        new_client["id"] = client_id
        
        return {
            "message": "Client created successfully",
            "client": new_client
        }
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        raise HTTPException(status_code=500, detail="Failed to create client")

@router.put("/clients/{client_id}")
async def update_client(
    client_id: str,
    update_data: ClientUpdate,
    request: Request
) -> Dict[str, Any]:
    """Update an existing client"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc_ref = db.collection("clients").document(client_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Prepare update data
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if "name" in update_dict:
            update_dict["client_slug"] = generate_client_slug(update_dict["name"])
        
        update_dict["updated_at"] = datetime.utcnow().isoformat()
        
        # Update document
        doc_ref.update(update_dict)
        
        # Get updated document
        updated_doc = doc_ref.get()
        client_data = updated_doc.to_dict()
        client_data["id"] = client_id
        
        return {
            "message": "Client updated successfully",
            "client": client_data
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update client")

@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    request: Request
) -> Dict[str, Any]:
    """Delete a client (soft delete by setting is_active=False)"""
    get_current_user_from_session(request)
    try:
        db = get_db()
        doc_ref = db.collection("clients").document(client_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Soft delete
        doc_ref.update({
            "is_active": False,
            "updated_at": datetime.utcnow().isoformat()
        })
        
        return {"message": "Client deactivated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete client")
```

---

## 🎨 Frontend Implementation

### **HTML Structure**

**File: `frontend/public/calendar_master.html` (relevant sections)**

```html
<!-- Client Selection Modal -->
<div id="clientModal" class="modal-backdrop">
    <div class="modal-content">
        <h3 class="text-2xl font-black gradient-text mb-6">Select Client</h3>
        <div class="grid gap-3" id="clientList">
            <!-- Clients will be loaded here -->
        </div>
        <button onclick="closeClientModal()" class="glow-button w-full mt-6">Cancel</button>
    </div>
</div>

<!-- Selected Client Display -->
<div class="flex items-center gap-3">
    <span class="text-white/60">Client:</span>
    <button onclick="openClientModal()" class="glass-card px-4 py-2 text-left hover:border-purple-500/50 transition-all">
        <span id="selectedClientName">Select Client</span>
    </button>
</div>

<!-- Loading Screen -->
<div id="loadingScreen" class="loading-screen">
    <div class="loading-content">
        <div class="loading-spinner"></div>
        <div id="loadingMessage" class="loading-message">Pre-flight checks in progress... 🛫</div>
    </div>
</div>
```

### **JavaScript Functions**

```javascript
class CalendarManager {
    constructor() {
        this.clients = [];
        this.selectedClient = null;
    }

    async loadClients() {
        // Show loading screen with aviation messages
        const loadingScreen = document.getElementById('loadingScreen');
        const loadingMessage = document.getElementById('loadingMessage');
        const messages = [
            "Pre-flight checks in progress... 🛫",
            "Fueling up the email engines... ⛽",
            "Calibrating campaign altitude... 📐",
            "Checking wind conditions for optimal delivery... 🌬️",
            "Loading passenger manifest (your clients)... 📋",
            "Tower, we're ready for departure... 🗼"
        ];
        
        loadingScreen.style.display = 'flex';
        let messageIndex = 0;
        
        // Rotate through messages
        const messageInterval = setInterval(() => {
            messageIndex = (messageIndex + 1) % messages.length;
            loadingMessage.textContent = messages[messageIndex];
        }, 2000);
        
        try {
            const response = await fetch('/api/admin/clients');
            if (response.ok) {
                const data = await response.json();
                this.clients = data.clients.filter(client => client.is_active && client.has_klaviyo_key);
                this.renderClientList();
                showToast(`✈️ Cleared for landing with ${this.clients.length} active clients`);
            } else {
                // Fallback to demo clients
                this.clients = [
                    { id: 'demo-1', name: 'Demo Company', client_slug: 'demo' },
                    { id: 'demo-2', name: 'Test Brand', client_slug: 'test' }
                ];
                this.renderClientList();
                showToast('Using demo flight plan (demo clients)');
            }
        } catch (error) {
            console.error('Failed to load clients:', error);
            showToast('⚠️ Turbulence detected - using backup flight plan', 'warning');
        } finally {
            // Hide loading screen
            clearInterval(messageInterval);
            setTimeout(() => {
                loadingScreen.style.display = 'none';
            }, 500);
        }
    }
    
    renderClientList() {
        const list = document.getElementById('clientList');
        list.innerHTML = this.clients.map(client => `
            <button onclick="selectClient('${client.id}')" class="glass-card p-4 text-left hover:border-purple-500/50 transition-all">
                <div class="font-bold">${client.name}</div>
                <div class="text-sm text-white/50">${client.client_slug}</div>
            </button>
        `).join('');
    }
    
    selectClient(clientId) {
        this.selectedClient = this.clients.find(c => c.id === clientId);
        document.getElementById('selectedClientName').textContent = this.selectedClient.name;
        closeClientModal();
        // Load existing calendar data for this client
        this.loadFromCloud();
    }
}

// Global functions
function openClientModal() {
    document.getElementById('clientModal').classList.add('show');
}

function closeClientModal() {
    document.getElementById('clientModal').classList.remove('show');
}

function selectClient(clientId) {
    calendarManager.selectClient(clientId);
}

function showToast(message, type = 'info') {
    // Toast notification implementation
    console.log(`[${type.toUpperCase()}] ${message}`);
}

// Initialize calendar manager
const calendarManager = new CalendarManager();

// Load clients on page load
document.addEventListener('DOMContentLoaded', async () => {
    await calendarManager.loadClients();
});
```

### **CSS Styles**

```css
/* Modal Styles */
.modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
}

.modal-backdrop.show {
    opacity: 1;
    visibility: visible;
}

.modal-content {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 2rem;
    max-width: 500px;
    width: 90%;
    max-height: 80vh;
    overflow-y: auto;
}

/* Loading Screen */
.loading-screen {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.9);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 2000;
}

.loading-content {
    text-align: center;
    color: white;
}

.loading-spinner {
    width: 50px;
    height: 50px;
    border: 3px solid rgba(255, 255, 255, 0.3);
    border-top: 3px solid #ffffff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin: 0 auto 1rem;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Glass Card Styles */
.glass-card {
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    backdrop-filter: blur(10px);
    transition: all 0.3s ease;
}

.glass-card:hover {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(138, 108, 247, 0.3);
    transform: translateY(-2px);
}
```

---

## ⚙️ Configuration Requirements

### **Environment Variables**

**File: `.env` or system environment**
```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GCLOUD_PROJECT=your-project-id

# Firestore Configuration
FIRESTORE_EMULATOR_HOST=127.0.0.1:8080  # For local development
FIRESTORE_TRANSPORT=rest                  # For better local development

# Secret Manager Configuration
SECRET_MANAGER_ENABLED=true
SECRET_MANAGER_TRANSPORT=rest

# Application Configuration
ENVIRONMENT=development  # or production
DEBUG=true              # For development only
```

### **Python Dependencies**

**File: `requirements.txt` (additions needed)**
```txt
fastapi>=0.112
google-cloud-firestore>=2.17
google-cloud-secret-manager>=2.16.0
google-oauth2-tool>=0.0.3
uvicorn[standard]>=0.30
python-dotenv>=1.0
httpx>=0.24.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
python-multipart>=0.0.6
```

### **Google Cloud Setup**

1. **Enable APIs:**
   ```bash
   gcloud services enable firestore.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   ```

2. **Create Firestore Database:**
   ```bash
   gcloud firestore databases create --region=us-central1
   ```

3. **Setup Service Account:**
   ```bash
   gcloud iam service-accounts create emailpilot-service \
     --display-name="EmailPilot Service Account"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:emailpilot-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/datastore.user"
   
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:emailpilot-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

---

## 🔧 Integration Setup

### **1. Router Registration**

**File: `main_firestore.py` (modifications needed)**

```python
# Add import
from app.api.admin_clients import router as admin_clients_router

# Add router registration (around line 861)
app.include_router(admin_clients_router, tags=["Admin Client Management"])
```

### **2. Session Middleware**

**File: `main_firestore.py` (ensure this exists)**

```python
from starlette.middleware.sessions import SessionMiddleware

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-here")
```

### **3. CORS Configuration**

**File: `main_firestore.py` (ensure this exists)**

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 🚀 Step-by-Step Build Instructions

### **Phase 1: Database Setup**

1. **Setup Google Cloud Project**
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   gcloud config set project $GOOGLE_CLOUD_PROJECT
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable firestore.googleapis.com secretmanager.googleapis.com
   ```

3. **Create Firestore Database**
   ```bash
   gcloud firestore databases create --region=us-central1
   ```

4. **Add Sample Client Data**
   ```bash
   # Use Firestore console or script to add:
   {
     "name": "Test Client",
     "client_slug": "test-client", 
     "is_active": true,
     "has_klaviyo_key": true
   }
   ```

### **Phase 2: Backend Implementation**

1. **Create Dependency Files**
   - Create `app/deps/firestore.py`
   - Create `app/services/secrets.py`
   - Create `app/services/client_key_resolver.py`
   - Update `app/deps/__init__.py`

2. **Create API Router**
   - Create `app/api/admin_clients.py`
   - Test endpoint: `GET /api/admin/clients`

3. **Register Router**
   - Modify `main_firestore.py` to include router
   - Test API availability

### **Phase 3: Frontend Implementation**

1. **Add HTML Structure**
   - Add modal HTML to `calendar_master.html`
   - Add client selection button

2. **Implement JavaScript**
   - Add `CalendarManager` class
   - Implement `loadClients()` function
   - Implement client selection logic

3. **Add CSS Styles**
   - Add modal styles
   - Add loading screen styles
   - Add glass card effects

### **Phase 4: Testing & Integration**

1. **Test API Endpoints**
   ```bash
   curl http://localhost:8000/api/admin/clients
   ```

2. **Test Frontend Integration**
   - Load calendar page
   - Verify clients load in dropdown
   - Test client selection

3. **Test Error Handling**
   - Test with database offline
   - Test with invalid data
   - Verify fallback behavior

### **Phase 5: Production Setup**

1. **Configure Production Environment**
   - Set production environment variables
   - Setup production Firestore
   - Configure Secret Manager

2. **Deploy Application**
   - Build application
   - Deploy to production environment
   - Test production functionality

---

## 🔍 Testing Instructions

### **Backend API Testing**

```bash
# Test client list endpoint
curl -X GET http://localhost:8000/api/admin/clients \
  -H "Content-Type: application/json"

# Test client details endpoint  
curl -X GET http://localhost:8000/api/admin/clients/CLIENT_ID \
  -H "Content-Type: application/json"

# Test client creation
curl -X POST http://localhost:8000/api/admin/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Client", "contact_email": "test@client.com"}'
```

### **Frontend Testing**

1. **Load Calendar Page**
   - Open `http://localhost:8000/static/calendar_master.html`
   - Verify loading screen appears
   - Check browser console for errors

2. **Test Client Dropdown**
   - Click "Select Client" button
   - Verify modal opens with client list
   - Select a client and verify selection

3. **Test Error Scenarios**
   - Test with Firestore offline
   - Test with invalid API responses
   - Verify fallback behavior works

### **Integration Testing**

```javascript
// Browser console tests
// Test client loading
await calendarManager.loadClients();
console.log('Loaded clients:', calendarManager.clients);

// Test client selection
calendarManager.selectClient('client-id');
console.log('Selected client:', calendarManager.selectedClient);
```

---

## 🐛 Troubleshooting Guide

### **Common Issues & Solutions**

#### **1. "No clients appearing in dropdown"**
- **Check:** API endpoint returns data: `curl http://localhost:8000/api/admin/clients`
- **Check:** Client filter criteria: `is_active=true AND has_klaviyo_key=true`
- **Check:** Browser console for JavaScript errors
- **Fix:** Add clients with correct properties to Firestore

#### **2. "Firestore connection failed"**
- **Check:** Environment variable `GOOGLE_CLOUD_PROJECT` is set
- **Check:** Firestore database exists and is accessible
- **Check:** Service account has proper permissions
- **Fix:** Run `gcloud auth application-default login` for local development

#### **3. "Authentication required error"**
- **Check:** Session middleware is configured in `main_firestore.py`
- **Check:** Development mode bypass is working
- **Fix:** Ensure `ENVIRONMENT=development` for local testing

#### **4. "Secret Manager access denied"**
- **Check:** Service account has `secretmanager.secretAccessor` role
- **Check:** Secret names match expected format
- **Fix:** Update IAM permissions or use environment variables for local testing

#### **5. "Frontend not loading clients"**
- **Check:** API endpoint is accessible from frontend
- **Check:** CORS is properly configured
- **Check:** Network tab in browser dev tools for failed requests
- **Fix:** Verify API URL and CORS middleware setup

### **Debug Commands**

```bash
# Check Firestore connection
gcloud firestore databases list

# Test API endpoint
curl -v http://localhost:8000/api/admin/clients

# Check application logs
tail -f logs/emailpilot_app.log

# Verify environment variables
env | grep GOOGLE_CLOUD_PROJECT
```

### **Development vs Production Differences**

| Component | Development | Production |
|-----------|-------------|------------|
| Authentication | Session bypass | Full auth required |
| Firestore | Emulator or real | Real database |
| Secret Manager | Optional | Required |
| API Keys | Environment vars | Secret Manager |
| CORS | Localhost only | Specific domains |

---

## 📚 Additional Resources

### **Documentation Links**
- [Google Cloud Firestore Documentation](https://cloud.google.com/firestore/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Secret Manager](https://cloud.google.com/secret-manager/docs)

### **Example API Responses**

**GET /api/admin/clients**
```json
{
  "clients": [
    {
      "id": "client-123",
      "name": "Acme Corporation",
      "client_slug": "acme-corporation",
      "is_active": true,
      "has_klaviyo_key": true,
      "contact_email": "contact@acme.com",
      "industry": "E-commerce",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "active_count": 1,
  "with_keys_count": 1
}
```

### **Sample Firestore Data**

```javascript
// Collection: clients
// Document: auto-generated-id
{
  "name": "Rogue Creamery",
  "client_slug": "rogue-creamery",
  "is_active": true,
  "has_klaviyo_key": true,
  "klaviyo_api_key_secret": "klaviyo-api-key-rogue-creamery",
  "contact_email": "info@roguecreamery.com",
  "industry": "Food & Beverage",
  "notes": "Artisanal cheese company",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

---

## ✅ Verification Checklist

### **Backend Verification**
- [ ] Firestore connection working
- [ ] API endpoints returning data
- [ ] Client filtering working correctly
- [ ] Authentication bypass working in development
- [ ] Secret Manager integration functional
- [ ] Error handling working properly

### **Frontend Verification**
- [ ] Client modal opens and closes
- [ ] Clients load in dropdown
- [ ] Client selection updates display
- [ ] Loading screen appears during fetch
- [ ] Error handling shows appropriate messages
- [ ] CSS styles render correctly

### **Integration Verification**
- [ ] API router mounted in main application
- [ ] CORS configured for frontend
- [ ] Session middleware working
- [ ] Environment variables set correctly
- [ ] Database contains sample client data
- [ ] End-to-end client selection flow working

---

**🎉 Congratulations! You now have a complete, functional client dropdown system.**

This documentation provides everything needed to rebuild the client dropdown functionality from scratch, including all required files, configurations, and step-by-step instructions.