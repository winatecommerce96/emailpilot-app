# EmailPilot Automated Deployment System

A comprehensive automated deployment system for EmailPilot that properly integrates frontend features, manages services, and ensures successful production deployments.

## 🚀 Quick Start - Deploy MCP Management Interface

**One command to deploy everything:**

```bash
./deploy_mcp_complete.sh
```

This will:
- ✅ Stop EmailPilot services
- ✅ Register MCP Management component in React app  
- ✅ Add "MCP Management" to Admin menu
- ✅ Configure routing for `/admin/mcp`
- ✅ Build and deploy to Google Cloud Run
- ✅ Restart services
- ✅ Verify deployment success
- ✅ Generate deployment report

## 📋 System Components

### 1. Master Deployment Script (`deploy_master.sh`)

The main deployment orchestrator that handles complete feature deployments.

```bash
# Deploy specific features
./deploy_master.sh --feature mcp           # Deploy MCP Management
./deploy_master.sh --feature calendar      # Deploy Calendar feature
./deploy_master.sh --feature admin         # Deploy Admin feature

# Full deployment
./deploy_master.sh                         # Deploy all features

# Options
./deploy_master.sh --dry-run               # Preview changes
./deploy_master.sh --no-rollback           # Disable auto-rollback
./deploy_master.sh --skip-health-check     # Skip health verification
```

### 2. Service Manager (`scripts/service_manager.sh`)

Manages Cloud Run service lifecycle:

```bash
# Service status and control
./scripts/service_manager.sh status        # Check service status
./scripts/service_manager.sh stop          # Stop service
./scripts/service_manager.sh start         # Start service
./scripts/service_manager.sh restart       # Restart service
./scripts/service_manager.sh scale 0 10    # Scale to 0-10 instances

# Monitoring and logs
./scripts/service_manager.sh logs 100      # Show last 100 log entries
./scripts/service_manager.sh monitor       # Real-time monitoring
```

### 3. Component Registrar (`scripts/component_registrar.py`)

Automatically registers React components in the production build:

```bash
# Scan existing components
python3 scripts/component_registrar.py scan

# Register new component
python3 scripts/component_registrar.py register MCPManagement \
    --menu-label "MCP Management" --icon "🤖" --admin-only

# Generate registration report
python3 scripts/component_registrar.py report --output registration_report.json
```

### 4. Health Checker (`scripts/health_checker.py`)

Comprehensive health monitoring and verification:

```bash
# Basic health check
python3 scripts/health_checker.py --category all

# Specific category checks
python3 scripts/health_checker.py --category basic      # Basic endpoints
python3 scripts/health_checker.py --category api        # API endpoints  
python3 scripts/health_checker.py --category frontend   # Frontend assets
python3 scripts/health_checker.py --category mcp        # MCP integration
python3 scripts/health_checker.py --category performance # Performance metrics

# Continuous monitoring
python3 scripts/health_checker.py --monitor --interval 60 --duration 30

# With authentication
python3 scripts/health_checker.py --auth-token "your-jwt-token"
```

### 5. Rollback Manager (`scripts/rollback_manager.sh`)

Handles deployment rollbacks and recovery:

```bash
# View deployment history
./scripts/rollback_manager.sh list         # List available revisions
./scripts/rollback_manager.sh current      # Show current revision

# Rollback operations
./scripts/rollback_manager.sh previous     # Rollback to previous version
./scripts/rollback_manager.sh emergency    # Emergency rollback (immediate)
./scripts/rollback_manager.sh interactive  # Interactive rollback selection

# Canary rollback (gradual traffic shift)
./scripts/rollback_manager.sh canary emailpilot-api-00042-xyz 10 60

# Backup operations
./scripts/rollback_manager.sh backup       # Create rollback backup
./scripts/rollback_manager.sh validate emailpilot-api-00042-xyz  # Validate target
```

## 🔧 Configuration

### Environment Setup

The deployment system automatically detects and configures:

- **Project ID**: `emailpilot-438321`
- **Service Name**: `emailpilot-api`  
- **Region**: `us-central1`
- **Production URL**: `https://emailpilot.ai`

### Required Google Cloud APIs

The system automatically enables required APIs:
- Cloud Run API (`run.googleapis.com`)
- Cloud Build API (`cloudbuild.googleapis.com`)
- Secret Manager API (`secretmanager.googleapis.com`)

### Authentication

Ensure you're authenticated with Google Cloud:

```bash
gcloud auth login
gcloud config set project emailpilot-438321
```

## 📊 Deployment Flow

### Automatic Deployment Process

1. **Pre-deployment Checks**
   - Verify authentication
   - Check required APIs
   - Validate file structure
   - Test prerequisites

2. **Service Management**
   - Stop Cloud Run service (scale to 0)
   - Create deployment backup
   - Log current state

3. **Frontend Integration**  
   - Register React components in `index.html`
   - Add menu items to admin navigation
   - Configure routing in `app.js`
   - Update component dependencies

4. **Build & Deploy**
   - Trigger Google Cloud Build
   - Build Docker container
   - Deploy to Cloud Run
   - Update service configuration

5. **Service Restart**
   - Scale service back up
   - Wait for readiness
   - Restore traffic

6. **Verification**
   - Run comprehensive health checks
   - Test feature-specific endpoints
   - Verify frontend accessibility
   - Generate deployment report

7. **Rollback (if needed)**
   - Automatic rollback on failure
   - Restore previous revision
   - Alert with failure details

## 📈 Monitoring & Health Checks

### Health Check Categories

- **Basic Health**: Root endpoints, health status, frontend app
- **API Endpoints**: Authentication, protected routes, public APIs
- **Frontend Assets**: JavaScript files, components, images
- **MCP Integration**: MCP-specific endpoints and functionality  
- **Performance**: Response times, resource usage

### Automated Monitoring

The system includes automated monitoring with:
- Real-time health status
- Performance metrics
- Error detection
- Alert generation
- Historical reporting

## 🎯 Feature-Specific Deployments

### MCP Management Interface

Deploy the complete MCP management system:

```bash
./deploy_mcp_complete.sh
```

**What gets deployed:**
- MCP Management React component
- Admin menu integration  
- MCP API endpoints (`/api/mcp/*`)
- Firestore synchronization
- Connection testing interface
- Usage statistics dashboard

**Access:** https://emailpilot.ai/app → Admin → MCP Management

### Calendar Features

```bash
./deploy_master.sh --feature calendar
```

**Includes:**
- Interactive campaign calendar
- Drag-and-drop functionality
- Goals-aware planning
- Firebase integration

### Admin Dashboard

```bash  
./deploy_master.sh --feature admin
```

**Features:**
- User management
- System configuration
- Performance monitoring
- Security settings

## 🔒 Security & Best Practices

### Deployment Security

- **Authentication required** for all deployment operations
- **Secret Manager integration** for sensitive configuration
- **Backup creation** before any changes
- **Rollback capabilities** for quick recovery
- **Health verification** before marking deployment complete

### Production Safety

- **Service isolation** during deployment
- **Zero-downtime deployments** with proper scaling
- **Comprehensive testing** before traffic restoration
- **Automatic rollback** on failure detection
- **Audit logging** of all deployment actions

## 🚨 Troubleshooting

### Common Issues

**Deployment fails with authentication error:**
```bash
gcloud auth login
gcloud config set project emailpilot-438321
```

**Component not showing in production:**
```bash
# Check component registration
python3 scripts/component_registrar.py report

# Verify health
python3 scripts/health_checker.py --category frontend
```

**Service not starting after deployment:**
```bash
# Check service status  
./scripts/service_manager.sh status

# View recent logs
./scripts/service_manager.sh logs 50

# Emergency rollback if needed
./scripts/rollback_manager.sh emergency
```

**MCP interface not accessible:**
```bash
# Test MCP endpoints
python3 scripts/health_checker.py --category mcp

# Check if user has admin access
# Must be logged in as: damon@winatecommerce.com or admin@emailpilot.ai
```

### Recovery Procedures

**Emergency rollback:**
```bash
./scripts/rollback_manager.sh emergency
```

**Restore from backup:**
```bash  
./scripts/rollback_manager.sh list
./scripts/rollback_manager.sh rollback <revision-name>
```

**Manual component removal:**
```bash
python3 scripts/component_registrar.py unregister MCPManagement
./deploy_master.sh --feature admin  # Redeploy without MCP
```

## 📞 Support

For deployment issues:

1. **Check logs**: `./scripts/service_manager.sh logs`
2. **Run diagnostics**: `python3 scripts/health_checker.py`  
3. **Review backups**: Check `deployments/backups/` directory
4. **Emergency rollback**: `./scripts/rollback_manager.sh emergency`

## 🎉 Success Indicators

✅ **Deployment completed successfully**  
✅ **All health checks passing**  
✅ **MCP Management visible in Admin menu**  
✅ **Service responding at https://emailpilot.ai**  
✅ **Deployment report generated**

---

*EmailPilot Automated Deployment System v1.0.0*  
*Created for seamless production deployments with full rollback capabilities*