# 🚀 EmailPilot Setup Guide
## Transform Your Klaviyo Tools into a Professional Web App

### 🎯 **Overview**
This guide will help you deploy EmailPilot - a professional web application that wraps your existing Klaviyo automation tools with a modern API and web interface.

---

## 📋 **What's Been Created**

### ✅ **Backend (FastAPI)**
- **Complete REST API** with endpoints for reports, goals, clients, and Slack integration
- **Database models** for PostgreSQL/SQLite
- **Authentication system** with JWT tokens
- **Background task processing** for long-running reports
- **Service layer** that wraps your existing Python scripts
- **Docker containerization** ready for Cloud Run

### ✅ **Frontend (React)**
- **Modern dashboard** with real-time stats
- **Report generation** with progress tracking
- **Goal management** interface
- **Client overview** and management
- **Responsive design** with Tailwind CSS

### ✅ **Deployment**
- **Cloud Run configuration** with auto-scaling
- **Cloud Build** for CI/CD pipeline
- **Domain mapping** ready for emailpilot.ai
- **Environment variables** for production secrets

---

## 🚀 **Quick Deploy (5 Minutes)**

### Step 1: Navigate to Your EmailPilot App
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app
```

### Step 2: Set Your Google Cloud Project
```bash
# Set your project ID
gcloud config set project YOUR-PROJECT-ID

# Verify it's set
gcloud config get-value project
```

### Step 3: Deploy to Cloud Run
```bash
# Make deploy script executable (if not already)
chmod +x deploy.sh

# Deploy everything at once
./deploy.sh
```

### Step 4: Test Your Deployment
After deployment completes, you'll get a URL like:
`https://emailpilot-api-XXXXXXX-uc.a.run.app`

Test it:
- **API**: `https://your-url.run.app/health`
- **Web App**: `https://your-url.run.app/` 
- **API Docs**: `https://your-url.run.app/docs`

---

## 🔧 **Configuration**

### Environment Variables for Production
Set these in Cloud Run:

```bash
# Set environment variables
gcloud run services update emailpilot-api \
  --region=us-central1 \
  --set-env-vars="
ENVIRONMENT=production,
DATABASE_URL=your-cloud-sql-connection-string,
SECRET_KEY=your-jwt-secret-key,
SLACK_WEBHOOK_URL=https://hooks.slack.com/your/webhook/url,
GEMINI_API_KEY=your-gemini-api-key
"
```

### Domain Mapping
Map your custom domain:

```bash
# Map emailpilot.ai to your service
gcloud run domain-mappings create \
  --service emailpilot-api \
  --domain emailpilot.ai \
  --region us-central1
```

---

## 📊 **API Endpoints**

### **Authentication**
- `POST /api/auth/login` - Login with email/password
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/logout` - Logout

### **Reports**
- `GET /api/reports/` - List all reports
- `POST /api/reports/weekly/generate` - Generate weekly report
- `POST /api/reports/monthly/generate` - Generate monthly report
- `GET /api/reports/latest/weekly` - Get latest weekly report
- `GET /api/reports/latest/monthly` - Get latest monthly report

### **Goals**
- `GET /api/goals/clients` - Get all clients with goal summary
- `GET /api/goals/{client_id}` - Get goals for specific client
- `POST /api/goals/{client_id}` - Create/update goal for client
- `POST /api/goals/generate` - Generate AI-powered goals

### **Clients**
- `GET /api/clients/` - List all clients
- `POST /api/clients/` - Create new client
- `GET /api/clients/{client_id}` - Get client details
- `PUT /api/clients/{client_id}` - Update client

### **Slack**
- `POST /api/slack/webhook/test` - Test Slack webhook
- `POST /api/slack/commands/weekly-report` - Handle /weekly-report
- `POST /api/slack/commands/monthly-report` - Handle /monthly-report

---

## 🔐 **Security Features**

### **Authentication**
- JWT token-based authentication
- Secure password hashing
- Token expiration and refresh
- Role-based access control ready

### **API Security**
- Request validation with Pydantic
- SQL injection protection with SQLAlchemy
- CORS configuration for frontend
- Rate limiting ready for implementation

### **Secrets Management**
- Environment variables for sensitive data
- Google Secret Manager integration ready
- API keys stored securely

---

## 🛠️ **How It Integrates Your Existing Tools**

### **Your Scripts → API Endpoints**
```python
# Your existing script:
weekly_performance_update.py

# Becomes API endpoint:
POST /api/reports/weekly/generate

# Still uses your exact code:
subprocess.run(["python3", "weekly_performance_update.py"])
```

### **Your JSON Files → Database**
```python
# Your existing files:
monthly_specific_goals.json
sales_goals.json

# Become database tables:
goals, clients, reports

# With migration scripts to import existing data
```

### **Your Slack Integration → Web API**
```python
# Your existing:
Slack webhook posts

# Become:
REST API endpoints that your team can trigger from web UI
Background tasks that still post to Slack
```

---

## 📱 **Web Interface Features**

### **Dashboard**
- Overview of all clients and their performance
- Quick action buttons to generate reports
- Real-time status of background tasks
- Statistics cards with key metrics

### **Reports Management**
- History of all generated reports
- Status tracking (pending, running, completed)
- Direct links to Slack posts
- Error handling and retry options

### **Goals Management** 
- Visual goal editor for all clients
- Bulk AI goal generation
- Manual override capabilities
- Historical goal tracking

### **Client Management**
- Add/edit/deactivate clients
- API key management
- Performance summaries
- Report history per client

---

## 🧪 **Testing Your Setup**

### **1. Test the API**
```bash
# Health check
curl https://your-url.run.app/health

# Login (get token)
curl -X POST https://your-url.run.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@emailpilot.ai", "password": "demo"}'

# Generate weekly report
curl -X POST https://your-url.run.app/api/reports/weekly/generate \
  -H "Authorization: Bearer YOUR-TOKEN"
```

### **2. Test the Web Interface**
- Visit your URL in browser
- Login with: `admin@emailpilot.ai` / `demo`
- Try generating a report
- Check that it posts to Slack

### **3. Test Slack Commands**
- Configure slash commands to point to your API
- Use `/weekly-report` in Slack
- Verify immediate response and background execution

---

## 📈 **Scaling & Production**

### **Database Setup**
For production, set up Cloud SQL:

```bash
# Create Cloud SQL instance
gcloud sql instances create emailpilot-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1

# Create database
gcloud sql databases create emailpilot --instance=emailpilot-db

# Update DATABASE_URL environment variable
```

### **Monitoring & Logging**
- Cloud Run provides automatic logging
- Set up uptime monitoring for your domain
- Configure alerts for failed report generations

### **Backup Strategy**
- Database backups via Cloud SQL
- Store your existing JSON files as initial data
- Version control for code changes

---

## 🎯 **Next Steps**

### **Immediate (This Week)**
1. ✅ Deploy basic version to Cloud Run
2. ✅ Test all API endpoints work
3. ✅ Configure your domain name
4. ✅ Set up Slack slash commands

### **Short Term (Next 2 Weeks)**
1. Migrate your existing data to database
2. Set up Cloud SQL for production
3. Configure proper authentication
4. Train your team on the web interface

### **Medium Term (Next Month)**
1. Add mobile-responsive design
2. Implement advanced reporting features
3. Set up automated backups
4. Add user management and roles

---

## 🆘 **Troubleshooting**

### **Deployment Issues**
```bash
# Check deployment logs
gcloud run services logs read emailpilot-api --region=us-central1

# Check service status
gcloud run services describe emailpilot-api --region=us-central1
```

### **API Issues**
- Check `/health` endpoint first
- Verify environment variables are set
- Check that existing Python scripts are accessible

### **Database Issues**
- Start with SQLite (default) for testing
- Migrate to Cloud SQL for production
- Verify connection strings

---

## 💡 **Pro Tips**

1. **Start Simple**: Deploy with SQLite first, migrate to Cloud SQL later
2. **Test Locally**: Run `python main.py` to test before deploying
3. **Use Staging**: Deploy to a staging environment first
4. **Monitor Costs**: Set up billing alerts in Google Cloud
5. **Keep Backups**: Your existing tools still work independently

---

## 🎉 **Success Criteria**

You'll know it's working when:
- ✅ Your team can access EmailPilot at emailpilot.ai
- ✅ Weekly reports generate from the web interface
- ✅ Goals can be managed through the UI
- ✅ Slack commands trigger reports
- ✅ All existing functionality is preserved

**Your Klaviyo tools are now a professional SaaS platform!** 🚀