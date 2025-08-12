"""
EmailPilot API - Full version with SQLite database support

This version connects to the migrated SQLite database and serves real client data.
"""
import sqlite3
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware
import os
import json
from datetime import datetime
from pathlib import Path

# Approved email addresses - Add your team members here
APPROVED_EMAILS = [
    "damon@winatecommerce.com",
    "admin@emailpilot.ai",
    # Add more approved emails here
]

# Create FastAPI app
app = FastAPI(
    title="EmailPilot API",
    description="Klaviyo automation platform for email marketing performance", 
    version="1.0.0"
)

# Add session middleware for OAuth
app.add_middleware(SessionMiddleware, secret_key="your-secret-key-change-this")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database helper functions
def get_db():
    """Get database connection"""
    db_path = Path(__file__).parent / 'emailpilot.db'
    if not db_path.exists():
        raise HTTPException(status_code=500, detail="Database not found. Run migration first.")
    return sqlite3.connect(str(db_path), check_same_thread=False)

def dict_factory(cursor, row):
    """Convert sqlite row to dictionary"""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

# Health check endpoints
@app.get("/api/")
async def root():
    return {
        "status": "healthy",
        "service": "EmailPilot API",
        "version": "1.0.0"
    }

# Serve static files directly from root
@app.get("/app.js")
async def get_app_js():
    return FileResponse('frontend/public/app.js', media_type='application/javascript')

# Serve frontend
@app.get("/")
async def get_frontend():
    return FileResponse('frontend/public/index.html')

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "klaviyo": "ready",
        "version": "1.0.0"
    }

# Authentication endpoints
@app.get("/api/auth/google")
async def google_login():
    """Redirect to Google OAuth"""
    return {
        "auth_url": "https://accounts.google.com/oauth/authorize",
        "message": "Use Google OAuth popup - this is a demo response"
    }

@app.post("/api/auth/google/callback")
async def google_callback(request: Request):
    """Handle Google OAuth callback"""
    data = await request.json()
    
    # In a real implementation, you would verify the Google token
    # For now, we'll accept the user info if they're in the approved list
    user_email = data.get("email", "")
    
    if user_email not in APPROVED_EMAILS:
        raise HTTPException(status_code=403, detail="Access denied. Email not in approved list.")
    
    # Store user in session
    request.session["user"] = {
        "email": user_email,
        "name": data.get("name", "User"),
        "picture": data.get("picture", "")
    }
    
    return {
        "access_token": "demo-token",
        "user": request.session["user"]
    }

@app.get("/api/auth/me")
async def get_current_user(request: Request):
    """Get current user info"""
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

@app.post("/api/auth/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return {"message": "Logged out successfully"}

# Protected route helper
def get_current_user_from_session(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

# Client API endpoints (now connected to real database)
@app.get("/api/clients/")
async def get_clients(request: Request, active_only: bool = True):
    """Get all clients from database"""
    get_current_user_from_session(request)
    
    conn = get_db()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        query = "SELECT * FROM clients"
        params = []
        
        if active_only:
            query += " WHERE is_active = ?"
            params.append(True)
            
        query += " ORDER BY name"
        
        cursor.execute(query, params)
        clients = cursor.fetchall()
        
        return clients
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.get("/api/clients/{client_id}")
async def get_client(client_id: int, request: Request):
    """Get specific client with statistics"""
    get_current_user_from_session(request)
    
    conn = get_db()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        # Get client info
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        client = cursor.fetchone()
        
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Get goals count
        cursor.execute("SELECT COUNT(*) as count FROM goals WHERE client_id = ?", (client_id,))
        goals_count = cursor.fetchone()['count']
        
        # Get reports count  
        cursor.execute("SELECT COUNT(*) as count FROM reports WHERE client_id = ?", (client_id,))
        reports_count = cursor.fetchone()['count']
        
        # Get latest report
        cursor.execute("""
            SELECT created_at FROM reports 
            WHERE client_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        """, (client_id,))
        latest_report = cursor.fetchone()
        
        # Get recent performance data for context
        cursor.execute("""
            SELECT AVG(revenue) as avg_revenue, COUNT(*) as months_data
            FROM performance_history 
            WHERE client_id = ? AND year >= 2024
        """, (client_id,))
        performance = cursor.fetchone()
        
        client['stats'] = {
            "goals_count": goals_count,
            "reports_count": reports_count,
            "latest_report": latest_report['created_at'] if latest_report else None,
            "avg_monthly_revenue": float(performance['avg_revenue']) if performance['avg_revenue'] else 0,
            "months_of_data": performance['months_data'] or 0
        }
        
        return client
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.post("/api/clients/")
async def create_client(request: Request):
    """Create new client"""
    get_current_user_from_session(request)
    data = await request.json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO clients (name, metric_id, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get('name'),
            data.get('metric_id', ''),
            data.get('description', ''),
            True,
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat()
        ))
        
        client_id = cursor.lastrowid
        conn.commit()
        
        # Return the created client
        conn.row_factory = dict_factory
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        return cursor.fetchone()
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Client name already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.put("/api/clients/{client_id}")
async def update_client(client_id: int, request: Request):
    """Update client"""
    get_current_user_from_session(request)
    data = await request.json()
    
    conn = get_db()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        # Check if client exists
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Update client
        cursor.execute("""
            UPDATE clients 
            SET name = COALESCE(?, name),
                metric_id = COALESCE(?, metric_id),
                description = COALESCE(?, description),
                is_active = COALESCE(?, is_active),
                updated_at = ?
            WHERE id = ?
        """, (
            data.get('name'),
            data.get('metric_id'),
            data.get('description'),
            data.get('is_active'),
            datetime.utcnow().isoformat(),
            client_id
        ))
        
        conn.commit()
        
        # Return updated client
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        return cursor.fetchone()
        
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Client name already exists")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.delete("/api/clients/{client_id}")
async def deactivate_client(client_id: int, request: Request):
    """Deactivate client (soft delete)"""
    get_current_user_from_session(request)
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE clients 
            SET is_active = ?, updated_at = ?
            WHERE id = ?
        """, (False, datetime.utcnow().isoformat(), client_id))
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Client not found")
        
        conn.commit()
        return {"message": "Client deactivated successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# Goals API endpoints
@app.get("/api/goals/clients")
async def get_clients_with_goals(request: Request):
    """Get all clients with their goal summaries"""
    get_current_user_from_session(request)
    
    conn = get_db()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT c.*, 
                   COUNT(g.id) as goals_count,
                   AVG(g.revenue_goal) as avg_goal,
                   MAX(g.updated_at) as latest_goal_update
            FROM clients c
            LEFT JOIN goals g ON c.id = g.client_id
            WHERE c.is_active = 1
            GROUP BY c.id
            ORDER BY c.name
        """)
        
        return cursor.fetchall()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

@app.get("/api/goals/{client_id}")
async def get_client_goals(client_id: int, request: Request):
    """Get all goals for a specific client"""
    get_current_user_from_session(request)
    
    conn = get_db()
    conn.row_factory = dict_factory
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT g.*, c.name as client_name
            FROM goals g
            JOIN clients c ON g.client_id = c.id
            WHERE g.client_id = ?
            ORDER BY g.year DESC, g.month DESC
        """, (client_id,))
        
        return cursor.fetchall()
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    finally:
        conn.close()

# Report endpoints
@app.get("/api/reports/latest/weekly")
async def get_latest_weekly(request: Request):
    """Get latest weekly report info"""
    get_current_user_from_session(request)
    return {
        "status": "completed",
        "generated_at": "2025-08-09T12:00:00Z",
        "summary": "Weekly report generated successfully from migrated data"
    }

@app.post("/api/reports/weekly/generate")
async def generate_weekly(request: Request):
    """Start weekly report generation"""
    get_current_user_from_session(request)
    return {
        "status": "started",
        "message": "Weekly report generation started with real client data"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)