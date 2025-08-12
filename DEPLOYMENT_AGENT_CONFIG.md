# 🚀 EmailPilot Deployment Agent Configuration

## Agent Role: `deployment-specialist`

### Purpose
A specialized AI agent that handles all deployment operations from local development (Claude chats) to Google Cloud Run production, with deep knowledge of your specific infrastructure and deployment patterns.

## Core Capabilities

### 1. **Deployment Automation**
- Direct Cloud Run deployments without GitHub
- Container image building and pushing
- Service revision management
- Traffic splitting and rollbacks
- Environment variable management

### 2. **Integration Management**
- Auto-integration of new features into existing containers
- Main application file patching (main_firestore.py)
- Route registration and API endpoint addition
- Database migration execution
- Service restart orchestration

### 3. **Package System Enhancement**
- Package upload system improvements
- Auto-integration trigger implementation
- Deployment confirmation dialogs
- Real-time progress monitoring
- Rollback mechanisms

### 4. **Cloud-Specific Knowledge**
- Google Cloud Run best practices
- Cloud Build configurations
- Cloud Shell command expertise
- GCP service account management
- Container Registry operations

## Agent Configuration

```yaml
agent_type: deployment-specialist
name: EmailPilot Deployment Specialist
version: 1.0.0

capabilities:
  - cloud_run_deployment
  - container_management
  - auto_integration
  - rollback_recovery
  - package_system_enhancement
  - monitoring_and_verification

knowledge_base:
  project_id: emailpilot-438321
  service_name: emailpilot-api
  region: us-central1
  deployment_method: direct_from_claude
  no_github: true
  
tools_available:
  - gcloud CLI
  - Cloud Shell
  - Cloud Build
  - Container Registry
  - Cloud Run
  - Cloud Functions (for proxies)
  - Firestore
  - Secret Manager

deployment_patterns:
  standard:
    - stage_files
    - build_container
    - push_to_registry
    - deploy_to_cloud_run
    - verify_deployment
    
  auto_integration:
    - backup_current_state
    - patch_main_application
    - install_new_modules
    - run_migrations
    - restart_service
    - verify_endpoints
    - monitor_health
```

## Deployment Agent Prompts

### When to Use the Deployment Agent

```markdown
Use the deployment-specialist agent when:
- Deploying new features to Cloud Run
- Integrating packages into production
- Fixing deployment issues
- Setting up auto-integration
- Troubleshooting 404 errors after deployment
- Creating deployment scripts
- Managing Cloud Run services
```

### Example Prompts for the Agent

1. **"Deploy the MCP package with auto-integration to Cloud Run"**
   - Agent will handle the complete deployment with integration

2. **"Fix the 404 errors for MCP endpoints in production"**
   - Agent will diagnose and fix integration issues

3. **"Create a deployment pipeline that auto-integrates packages"**
   - Agent will build the complete pipeline

4. **"Roll back the last deployment and restore previous version"**
   - Agent will handle safe rollback

5. **"Setup auto-deployment from Claude chats to Cloud Run"**
   - Agent will create the deployment workflow

## Implementation Script

```python
"""
Deployment Agent Implementation
This would be integrated into your Claude chat system
"""

class DeploymentAgent:
    def __init__(self):
        self.project_id = "emailpilot-438321"
        self.service_name = "emailpilot-api"
        self.region = "us-central1"
        self.deployment_method = "direct_from_claude"
        
    def deploy_with_integration(self, package_name, features):
        """
        Deploy a package with automatic integration
        """
        steps = [
            self.backup_current_deployment(),
            self.build_container_with_features(features),
            self.push_to_registry(),
            self.deploy_to_cloud_run(),
            self.verify_deployment(),
            self.test_endpoints()
        ]
        return self.execute_steps(steps)
    
    def fix_integration_issues(self, error_type):
        """
        Fix common integration problems
        """
        if error_type == "404_endpoints":
            return self.patch_missing_routes()
        elif error_type == "not_deployed":
            return self.force_deployment()
        elif error_type == "no_auto_integration":
            return self.add_auto_integration_support()
    
    def create_deployment_script(self, requirements):
        """
        Generate deployment scripts for specific needs
        """
        script = self.generate_cloud_run_deployment(requirements)
        script += self.add_integration_steps(requirements)
        script += self.add_verification_steps()
        script += self.add_rollback_capability()
        return script
    
    def monitor_deployment(self, deployment_id):
        """
        Real-time deployment monitoring
        """
        return {
            "status": self.check_deployment_status(deployment_id),
            "health": self.check_service_health(),
            "endpoints": self.verify_all_endpoints(),
            "logs": self.get_deployment_logs()
        }
```

## Deployment Agent Commands

### Cloud Shell Commands the Agent Would Generate

```bash
# 1. Deploy with auto-integration
cat > deploy_with_integration.sh << 'EOF'
#!/bin/bash
# Generated by Deployment Agent

# Backup current state
gcloud run services describe emailpilot-api --region=us-central1 --export > backup.yaml

# Build new container with integrated features
gcloud builds submit --config=cloudbuild-integrated.yaml

# Deploy with zero downtime
gcloud run deploy emailpilot-api \
  --image=gcr.io/emailpilot-438321/emailpilot-api:integrated \
  --region=us-central1 \
  --no-traffic

# Test new revision
./test_endpoints.sh

# If tests pass, migrate traffic
gcloud run services update-traffic emailpilot-api \
  --to-latest \
  --region=us-central1
EOF

# 2. Fix 404 errors
cat > fix_404_errors.sh << 'EOF'
#!/bin/bash
# Generated by Deployment Agent

# Check what's missing
curl -s https://emailpilot-api-935786836546.us-central1.run.app/api/mcp/models

# Patch the container
gcloud run services update emailpilot-api \
  --region=us-central1 \
  --update-env-vars="PATCH_MCP_ROUTES=true"

# Force restart
gcloud run services update-traffic emailpilot-api \
  --to-latest \
  --region=us-central1
EOF
```

## How to Use the Deployment Agent

### In Your Claude Chat

```markdown
@deployment-specialist Deploy the MCP package to production with auto-integration. 
The package was uploaded but endpoints return 404. Fix the integration and ensure 
all routes are properly registered in main_firestore.py.
```

### Expected Agent Response

```markdown
🚀 Deployment Specialist Agent Active

Analyzing deployment issue...
✅ Package uploaded: mcp-auto-integration-v2.0.0
❌ Integration not triggered: auto-integration not executed
❌ Routes not registered: /api/mcp/* returning 404

Executing fix sequence:
1. Creating integration patch script
2. Backing up current deployment
3. Patching main_firestore.py with MCP routes
4. Rebuilding container with integrated code
5. Deploying new revision to Cloud Run
6. Verifying endpoints respond correctly

[Provides specific Cloud Shell commands]
[Monitors deployment progress]
[Verifies successful integration]
```

## Benefits of the Deployment Agent

1. **Expertise**: Deep knowledge of your specific setup
2. **Automation**: Handles complex deployment workflows
3. **Safety**: Built-in backup and rollback
4. **Monitoring**: Real-time deployment tracking
5. **Integration**: Seamless feature addition
6. **No GitHub Required**: Works with direct Claude deployments

## Next Steps

1. **Add to Claude configuration**: Include deployment-specialist in available agents
2. **Test with current issue**: Use agent to fix MCP integration
3. **Enhance over time**: Agent learns from each deployment
4. **Document patterns**: Build knowledge base of successful deployments

This deployment agent would solve your current MCP integration issue and prevent similar problems in the future!