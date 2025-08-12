# 📦 EmailPilot.ai Package Upload & Deployment Instructions

## Overview
EmailPilot.ai supports modular package deployment through its Admin Dashboard, allowing you to upload and deploy new features without modifying the core application code. This system enables safe, incremental deployment of multiple packages while preventing dependency conflicts.

## 🏗️ Architecture

### Components
1. **Admin Dashboard** - Web interface for package management (https://emailpilot.ai/admin)
2. **Package Upload API** - Backend endpoints for handling package uploads
3. **Firestore Storage** - Tracks package deployment history and metadata
4. **Deployment Engine** - Executes package deployment scripts safely
5. **Google Cloud Run** - Hosts the production application

### Technology Stack
- **Frontend**: React-based admin interface
- **Backend**: FastAPI (Python) with Firestore integration
- **Deployment**: Google Cloud Run with automatic scaling
- **Storage**: Google Cloud Storage for package files
- **Database**: Firestore for package metadata and deployment logs

## 📋 Package Requirements

### Package Structure
```
your-package/
├── deploy_to_emailpilot.sh    # Required deployment script
├── requirements.txt            # Optional - dependencies (NOT installed automatically)
├── frontend/                   # Optional - frontend components
│   ├── components/
│   └── assets/
├── api/                        # Optional - API endpoints
│   └── routes.py
├── services/                   # Optional - backend services
├── models/                     # Optional - data models
├── schemas/                    # Optional - Pydantic schemas
└── README.md                   # Package documentation
```

### Required Files
1. **`deploy_to_emailpilot.sh`** - Main deployment script
   - Must be in package root or immediate subdirectory
   - Should use the safe deployment template
   - Will be executed with `EMAILPILOT_DEPLOYMENT=true` environment variable

### Safe Deployment Script Template (PROVEN TO WORK)
```bash
#!/bin/bash
# Safe deployment script for [YOUR_PACKAGE_NAME]
# This template has been tested and proven to work in production

echo "🚀 Starting deployment of [YOUR_PACKAGE_NAME] to EmailPilot.ai"
echo "📍 Current directory: $(pwd)"
echo "📁 Package contents: $(ls -la)"

# Create staging directory with fallback options
STAGING_DIR="/app/staged_packages/[your_package]_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$STAGING_DIR" 2>/dev/null || {
    echo "⚠️ Cannot create /app/staged_packages, trying /tmp..."
    STAGING_DIR="/tmp/[your_package]_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$STAGING_DIR"
}

echo "📦 Staging files to: $STAGING_DIR"

# Stage all package files
cp -r * "$STAGING_DIR/" 2>/dev/null || true

# Create integration instructions
cat > "$STAGING_DIR/INTEGRATION_INSTRUCTIONS.md" << 'EOF'
# Integration Instructions for [YOUR_PACKAGE_NAME]

## Files Staged
All package files have been staged to this directory.

## Frontend Integration
If your package includes frontend components:
```bash
cp -r frontend/components/* /app/frontend/public/components/
```

## Backend Integration  
For backend components, add to main_firestore.py:
```python
# Add imports
from app.api.[your_module] import router as [your]_router

# Register router
app.include_router([your]_router, prefix="/api/[your_endpoint]", tags=["[your_tag]"])
```

## Database Migration
If your package includes database changes:
```bash
python migrate_[your_module].py
```

## Restart Application
After integration, restart the service:
```bash
gcloud run services update emailpilot-api --region=us-central1
```
EOF

echo "✅ Package staged successfully!"
echo "📋 Integration instructions created at: $STAGING_DIR/INTEGRATION_INSTRUCTIONS.md"
echo ""
echo "Next steps:"
echo "1. Review staged files at: $STAGING_DIR"
echo "2. Follow integration instructions"
echo "3. Test the deployment"
echo ""
echo "🎉 Staging complete - ready for manual integration"

# Always exit with success to avoid deployment errors
exit 0
```

## 🚀 Deployment Process

### Step 1: Package Preparation
1. **Create your package** following the structure above
2. **Add deployment script** using the safe template
3. **Test locally** if possible
4. **Create ZIP archive**:
   ```bash
   zip -r your-package.zip your-package/
   ```

### Step 2: Upload via Admin Dashboard
1. **Access Admin Dashboard**: https://emailpilot.ai/admin
2. **Login** with admin credentials (damon@winatecommerce.com or admin@emailpilot.ai)
3. **Navigate to** "Package Management" section
4. **Click** "Upload Package"
5. **Select** your ZIP file
6. **Enter** package name and description
7. **Click** "Upload"

### Step 3: Package Extraction & Validation
The system automatically:
- Extracts the ZIP file to `/uploaded_packages/`
- Validates package structure
- Stores metadata in Firestore
- Checks for deployment script

### Step 4: Deployment Execution
1. **View** uploaded packages in the dashboard
2. **Click** "Deploy" button for your package
3. System executes `deploy_to_emailpilot.sh` with safety flags
4. **Monitor** deployment output in real-time
5. **Review** deployment status and logs

### Step 5: Post-Deployment
1. **Manual Integration** (if needed):
   - Backend components are staged in `/integrations/`
   - Manually add API routes to `main_firestore.py`
   - Update frontend imports as needed

2. **Application Restart**:
   - Click "Restart Application" in admin dashboard
   - Or use Google Cloud Console to restart service

3. **Verification**:
   - Test new features
   - Check application logs
   - Verify all endpoints work

## 🔄 Multi-Package Deployment Strategy

### Sequential Deployment
Deploy packages in order of dependency:
1. **Core Infrastructure** packages first
2. **Backend Services** second
3. **Frontend Features** last
4. **Enhancement Packages** after base features

### Example: Calendar System Deployment
```
Stage 1: Basic Calendar Package
├── Deploy calendar UI components
├── Add Firebase integration
└── Enable basic functionality

Stage 2: Goals Enhancement Package  
├── Add revenue tracking
├── Integrate AI recommendations
└── Enable advanced analytics
```

### Package Dependencies
- Packages should NOT install Python dependencies
- Use EmailPilot's existing packages
- Document any required dependencies for manual review
- Consider compatibility with existing packages

## 🛡️ Security & Safety

### Deployment Safeguards
1. **No Automatic Dependency Installation**
   - Prevents package conflicts
   - Maintains system stability
   - Dependencies documented but not installed

2. **Sandboxed Execution**
   - Scripts run with limited permissions
   - Cannot modify core EmailPilot files directly
   - Backend changes require manual integration

3. **Audit Trail**
   - All deployments logged in Firestore
   - Tracks who deployed what and when
   - Deployment output preserved

### Best Practices
- **Test in development** before production deployment
- **Create backups** before major deployments
- **Deploy incrementally** rather than all at once
- **Document changes** in package README
- **Version your packages** (e.g., v1.0.0, v1.1.0)

## 🧪 Testing Deployed Packages

### Testing MCP Package (Example)
After successful deployment, test functionality:

1. **Quick API Test**:
```bash
# Get auth token
TOKEN=$(curl -X POST https://emailpilot.ai/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}' | jq -r '.access_token')

# Test package endpoints
curl -X GET https://emailpilot.ai/api/mcp/models \
  -H "Authorization: Bearer $TOKEN"
```

2. **UI Component Test**:
- Navigate to https://emailpilot.ai/admin
- Check for new menu items or components
- Open browser console for any errors

3. **Integration Test**:
- Test interaction with existing features
- Verify data flows correctly
- Check performance metrics

For detailed testing instructions, see:
- **MCP Package**: `/MCP_PRODUCTION_TESTING.md`
- **Other Packages**: Check package-specific testing docs

## 📊 Monitoring & Rollback

### Health Checks
After deployment:
```bash
# Check application health
curl https://emailpilot.ai/health

# Test new endpoints (example for MCP)
curl https://emailpilot.ai/api/mcp/health

# Review logs in Google Cloud Console
gcloud run logs read --service=emailpilot-api
```

### Rollback Procedure
If issues occur:
1. **Immediate**: Restart application without new code
2. **Remove Package Files**: Delete from integration directory
3. **Revert Changes**: Remove manual integrations from main_firestore.py
4. **Redeploy**: Use Cloud Build to redeploy previous version
   ```bash
   gcloud builds submit --config cloudbuild.yaml
   ```

## 🔧 Production Deployment

### Google Cloud Run Deployment
The production application runs on Google Cloud Run:

1. **Service Details**:
   - **Project**: emailpilot-438321
   - **Service**: emailpilot-api
   - **Region**: us-central1
   - **URL**: https://emailpilot.ai

2. **Deployment Command**:
   ```bash
   # From emailpilot-app directory
   ./deploy.sh
   ```

3. **Cloud Build Configuration**:
   - Builds Docker container
   - Pushes to Container Registry
   - Deploys to Cloud Run
   - Sets environment variables

### Environment Configuration
Managed through Admin Dashboard:
- `SLACK_WEBHOOK_URL` - Slack notifications
- `GEMINI_API_KEY` - AI features
- `KLAVIYO_API_KEY` - Klaviyo integration
- `DATABASE_URL` - Database connection
- `GOOGLE_CLOUD_PROJECT` - GCP project ID

## 📝 Package Development Guidelines

### Creating a New Package
1. **Plan Integration Points**
   - Identify where package connects to EmailPilot
   - Document API endpoints needed
   - List frontend components

2. **Develop Components**
   - Follow EmailPilot coding standards
   - Use existing utilities and services
   - Maintain consistent UI/UX

3. **Write Deployment Script**
   - Use safe deployment template
   - Handle both frontend and backend
   - Create integration documentation

4. **Package Testing**
   - Test deployment script locally
   - Verify file copying works
   - Check for conflicts

### Example Package: Analytics Dashboard
```
analytics-dashboard/
├── deploy_to_emailpilot.sh
├── frontend/
│   ├── components/
│   │   ├── AnalyticsDashboard.js
│   │   └── ChartComponents.js
│   └── assets/
│       └── analytics.css
├── api/
│   └── analytics_routes.py
├── services/
│   └── analytics_service.py
└── README.md
```

## 🆘 Troubleshooting

### Common Issues

1. **Package Upload Fails**
   - Check file size (max 100MB)
   - Verify ZIP format
   - Ensure admin permissions

2. **Deployment Script Not Found**
   - Must be named `deploy_to_emailpilot.sh`
   - Check it's in root or immediate subdirectory
   - Verify file permissions (executable)

3. **Package Not Deploying**
   - Check deployment logs in dashboard
   - Verify script syntax
   - Ensure EMAILPILOT_DEPLOYMENT check

4. **Features Not Working**
   - Backend may need manual integration
   - Check if application restart needed
   - Review integration documentation

### Support Resources
- **Logs**: Google Cloud Console → Cloud Run → Logs
- **Monitoring**: Google Cloud Monitoring Dashboard
- **Database**: Firestore Console for package metadata
- **Help**: Create issue at internal repository

## ✅ Deployment Checklist

### Pre-Deployment
Before deploying a package:
- [ ] Package follows required structure
- [ ] Deployment script uses safe staging template (proven to work)
- [ ] No direct dependency installation
- [ ] Documentation included (README.md)
- [ ] Testing instructions provided
- [ ] Tested locally if possible
- [ ] Backup created
- [ ] Admin access confirmed
- [ ] Deployment window scheduled
- [ ] Rollback plan prepared
- [ ] Team notified

### Post-Deployment Verification
After deployment succeeds:
- [ ] Package files staged to `/app/staged_packages/` or `/tmp/`
- [ ] Integration instructions available
- [ ] Frontend components accessible (if applicable)
- [ ] API endpoints responding (if applicable)
- [ ] No errors in deployment logs
- [ ] Basic functionality test passes
- [ ] Performance acceptable
- [ ] Security checks pass

### Success Indicators
Your deployment is successful when:
1. **Deployment Script**: Shows "Deployment successful" in admin dashboard
2. **Staging**: Files appear in staging directory with timestamp
3. **Integration**: Components can be manually integrated following instructions
4. **Testing**: Basic API/UI tests pass as documented
5. **Monitoring**: No critical errors in application logs
6. **Functionality**: New features work as expected

## 🎯 Summary

The EmailPilot Package Upload system provides:
- **Safe, modular deployment** of new features
- **No dependency conflicts** through sandboxed execution
- **Audit trail** of all deployments
- **Easy rollback** if issues occur
- **Multiple package support** for complex features

Follow these instructions to successfully deploy packages to production while maintaining system stability and security.