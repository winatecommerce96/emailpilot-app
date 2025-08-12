# 🚀 EmailPilot React Calendar Feature - Complete Installation Guide

## Overview

This package provides **two installation methods** for the EmailPilot React Calendar Feature:

1. **🔧 Automated Shell Script Installation** - Fully automated setup
2. **📦 Manual Package Deployment** - Traditional staging approach

## Method 1: Automated Shell Script Installation (Recommended)

### Quick Installation
```bash
# Extract the package
unzip calendar-react-feature-with-installer.zip
cd calendar-react-feature

# Run the automated installer
sudo ./install-calendar-feature.sh
```

### What the Installer Does
✅ **Automatic Backup Creation** - Backs up existing files before changes  
✅ **Dependency Management** - Installs required npm packages  
✅ **Directory Structure** - Creates proper React feature module structure  
✅ **File Installation** - Copies all calendar components and services  
✅ **Environment Configuration** - Sets up all required environment variables  
✅ **Routing Integration** - Adds calendar route to existing React app  
✅ **API Endpoint Setup** - Adds backend endpoints for AI features  
✅ **Application Build** - Builds and validates the installation  
✅ **Service Restart** - Restarts application services  
✅ **Installation Validation** - Verifies everything works correctly  

### Installation Output Example
```bash
==================================================
EmailPilot React Calendar Feature Installer
==================================================

[INFO] Starting installation of React Calendar Feature...
[SUCCESS] Permissions check passed
[INFO] Creating backup of existing files...
[SUCCESS] Backup created at: /app/backups/calendar_backup_20241211_143022
[INFO] Installing required dependencies...
[SUCCESS] Dependencies installation complete
[INFO] Creating directory structure...
[SUCCESS] Directory structure created
[INFO] Installing React calendar feature files...
[SUCCESS] Feature files installed with proper permissions
[INFO] Setting up environment configuration...
[SUCCESS] Environment configuration complete
[INFO] Setting up React routing...
[SUCCESS] Calendar route added to /app/src/AppRoutes.jsx
[INFO] Setting up backend API endpoints...
[SUCCESS] Calendar API endpoints added to /app/main.py
[INFO] Building the application...
[SUCCESS] Application build complete
[INFO] Validating installation...
[SUCCESS] Installation validation passed!
[INFO] Restarting services...
[SUCCESS] Service restart commands executed

==================================================
✅ EmailPilot React Calendar Feature Installation Complete!
==================================================

🎉 What's New:
   • Modern React-based calendar with drag & drop
   • AI-powered campaign planning assistance
   • Real-time revenue goal tracking
   • Auto-save with Firebase integration
   • Mobile-responsive design

🚀 Access Your Calendar:
   • Navigate to: /calendar
   • Test at: /calendar/test (after adding test route)

📋 Next Steps:
   1. Test the calendar functionality
   2. Configure AI endpoints in your backend
   3. Review the installation report
   4. Train users on new features

📁 Backup Created: /app/backups/calendar_backup_20241211_143022
📊 Report Generated: /app/calendar-installation-report.txt

[SUCCESS] Installation completed successfully! 🎊
```

### Installation Commands
```bash
# Basic installation
./install-calendar-feature.sh

# Validation only
./install-calendar-feature.sh validate

# Help
./install-calendar-feature.sh help
```

### Rollback Support
```bash
# Interactive rollback with backup selection
./rollback-calendar-feature.sh

# Clean removal (no restoration)
./rollback-calendar-feature.sh clean

# List available backups
./rollback-calendar-feature.sh list
```

## Method 2: Manual Package Deployment

### Traditional Staging Deployment
```bash
# Make deployment script executable
chmod +x deploy_to_emailpilot.sh

# Create package
zip -r calendar-package.zip .

# Upload via EmailPilot Admin Dashboard
# Navigate to: https://emailpilot.ai/admin
# Upload calendar-package.zip
# Click "Deploy" button
```

### Manual Integration Steps
After staging deployment, follow the integration instructions:

1. **Copy Feature Module**
   ```bash
   cp -r src/features/calendar /app/src/features/
   ```

2. **Configure Environment**
   ```bash
   cp calendar/.env.example /app/.env.local
   # Edit .env.local with your configuration
   ```

3. **Add Routing**
   ```jsx
   // In AppRoutes.jsx
   import CalendarPage from './features/calendar/CalendarPage';
   <Route path="/calendar" element={<CalendarPage />} />
   ```

4. **Add API Endpoints**
   ```python
   # In main.py or main_firestore.py
   @app.post("/api/ai/summarize-calendar")
   @app.post("/api/ai/chat")
   ```

5. **Build and Restart**
   ```bash
   npm run build
   # Restart your services
   ```

## Feature Comparison

| Feature | Automated Script | Manual Deployment |
|---------|------------------|------------------|
| **Setup Time** | 2-5 minutes | 15-30 minutes |
| **Error Handling** | Automatic | Manual troubleshooting |
| **Backup Creation** | Automatic | Manual |
| **Validation** | Built-in | Manual verification |
| **Rollback** | One-command | Manual restoration |
| **Environment Setup** | Automatic | Manual configuration |
| **Route Integration** | Automatic | Manual code changes |
| **API Endpoints** | Automatic | Manual backend changes |
| **Service Restart** | Automatic | Manual restart |

## Installation Requirements

### System Requirements
- **OS**: Linux/Unix (Ubuntu, CentOS, etc.)
- **Node.js**: 16+ with npm
- **React**: 18+ 
- **TypeScript**: Support recommended
- **Firebase**: Account and project setup
- **Write Permissions**: To `/app` directory

### Pre-Installation Checklist
- [ ] Backup your application
- [ ] Verify you have admin/sudo access
- [ ] Ensure EmailPilot app is running
- [ ] Confirm Firebase project is set up
- [ ] Test that `/app` directory is writable
- [ ] Stop any running development servers

### Environment Variables Required
```bash
REACT_APP_FIREBASE_CONFIG_JSON='{"apiKey":"...","authDomain":"...","projectId":"..."}'
REACT_APP_APP_ID=emailpilot-prod
REACT_APP_API_BASE=https://emailpilot-api-935786836546.us-central1.run.app
REACT_APP_AI_BASE=https://emailpilot-api-935786836546.us-central1.run.app
REACT_APP_ENABLE_AI_CHAT=true
REACT_APP_ENABLE_DRAG_DROP=true
REACT_APP_ENABLE_GOALS_INTEGRATION=true
```

## Post-Installation

### Testing Your Installation
1. **Navigate to Calendar**
   - Go to `https://your-domain.com/calendar`
   - Should see client selector and calendar grid

2. **Test Basic Functionality**
   - Select a client
   - Create a test campaign
   - Verify auto-save works
   - Check goals integration

3. **Run Integration Tests**
   ```jsx
   // Add this route for testing
   <Route path="/calendar/test" element={<CalendarIntegrationTest />} />
   ```
   - Navigate to `/calendar/test`
   - Review all test results

### Configuration
1. **Configure AI Endpoints**
   - Implement Gemini API integration in backend
   - Test AI chat functionality

2. **Set Up Firebase Security Rules**
   ```javascript
   rules_version = '2';
   service cloud.firestore {
     match /databases/{database}/documents {
       match /artifacts/{appId}/public/{document=**} {
         allow read, write: if request.auth != null;
       }
     }
   }
   ```

3. **Train Users**
   - Document new calendar features
   - Provide user training sessions
   - Update help documentation

## Troubleshooting

### Common Issues

#### Installation Fails
```bash
# Check permissions
ls -la /app

# Verify package contents
unzip -l calendar-react-feature-with-installer.zip

# Run validation
./install-calendar-feature.sh validate
```

#### Calendar Not Loading
```bash
# Check console for errors
# Verify environment variables
grep REACT_APP /app/.env.local

# Check routing
grep CalendarPage /app/src/AppRoutes.jsx
```

#### AI Features Not Working
```bash
# Verify API endpoints exist
grep "summarize-calendar" /app/main.py

# Check environment variables
grep AI_BASE /app/.env.local

# Test endpoint manually
curl -X POST https://your-domain.com/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

### Getting Help

1. **Check Installation Report**
   ```bash
   cat /app/calendar-installation-report.txt
   ```

2. **Review Backup Location**
   ```bash
   ls -la /app/backups/calendar_backup_*
   ```

3. **Validate Installation**
   ```bash
   ./install-calendar-feature.sh validate
   ```

4. **Check Application Logs**
   ```bash
   # PM2
   pm2 logs

   # SystemD
   journalctl -u emailpilot -f

   # Cloud Run
   gcloud run logs read --service=emailpilot-api
   ```

## Rollback Instructions

### Emergency Rollback
If something goes wrong:
```bash
# Interactive rollback with backup selection
./rollback-calendar-feature.sh

# Or quick clean removal
./rollback-calendar-feature.sh clean
```

### What Rollback Does
- Removes calendar feature files
- Restores backed up files (if selected)
- Cleans environment variables
- Removes API endpoints
- Rebuilds application
- Restarts services

## Support

### Package Contents
- **📁 calendar/** - Complete React feature module
- **🔧 install-calendar-feature.sh** - Automated installer
- **↩️ rollback-calendar-feature.sh** - Rollback script
- **📋 integration-test.jsx** - Testing component
- **📖 Documentation** - Complete setup guides

### Contact & Resources
- **Installation Report**: Generated at `/app/calendar-installation-report.txt`
- **Backup Location**: `/app/backups/calendar_backup_*`
- **Feature Documentation**: `calendar/README.md`
- **Environment Example**: `calendar/.env.example`

## Summary

The automated shell script installation is the **recommended approach** for most users as it:
- Reduces installation time from 30 minutes to 5 minutes
- Eliminates configuration errors
- Provides automatic backup and rollback
- Includes comprehensive validation
- Handles all integration steps automatically

Choose the manual deployment method only if you need:
- Complete control over each step
- Custom modifications during installation
- Integration with existing deployment pipelines
- Understanding of each component before installation