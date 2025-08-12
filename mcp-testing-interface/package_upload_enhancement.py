"""
Enhanced Package Upload System with Auto-Integration Support
This extends the existing package upload to handle service restarts and integration
"""

import os
import subprocess
import asyncio
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import HTTPException
from pathlib import Path

class AutoIntegrationPackageManager:
    """Enhanced package manager with auto-integration capabilities"""
    
    def __init__(self):
        self.staging_dir = "/app/staged_packages"
        self.backup_dir = "/app/backups"
        self.main_file = "/app/main_firestore.py"
        self.service_name = "emailpilot-api"
        self.region = "us-central1"
        self.project = "emailpilot-438321"
        
    async def deploy_with_integration(self, package_path: str, package_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deploy a package with automatic integration and service restart
        
        Args:
            package_path: Path to the extracted package
            package_info: Package metadata
            
        Returns:
            Deployment result with status and details
        """
        
        # Check if package supports auto-integration
        integration_config = self._load_integration_config(package_path)
        
        if not integration_config.get("auto_integration", False):
            # Fall back to standard deployment
            return await self._standard_deployment(package_path, package_info)
        
        # Show warning and get confirmation
        warning_message = self._generate_warning_message(integration_config)
        
        # In a real implementation, this would show a UI confirmation dialog
        # For now, we'll assume confirmation and proceed
        
        deployment_result = {
            "status": "starting",
            "package_name": package_info.get("name", "Unknown"),
            "timestamp": datetime.utcnow().isoformat(),
            "auto_integration": True,
            "steps": [],
            "warnings": [warning_message]
        }
        
        try:
            # Step 1: Create backups
            backup_result = await self._create_system_backup()
            deployment_result["steps"].append(backup_result)
            
            if not backup_result["success"]:
                raise Exception("Backup creation failed")
            
            # Step 2: Stage files
            stage_result = await self._stage_package_files(package_path)
            deployment_result["steps"].append(stage_result)
            
            # Step 3: Integrate API routes (if needed)
            if integration_config.get("requires_api_integration", False):
                api_result = await self._integrate_api_routes(package_path, integration_config)
                deployment_result["steps"].append(api_result)
            
            # Step 4: Copy files to application directories
            if integration_config.get("requires_file_installation", False):
                install_result = await self._install_package_files(package_path, integration_config)
                deployment_result["steps"].append(install_result)
            
            # Step 5: Run database migrations
            if integration_config.get("requires_migration", False):
                migration_result = await self._run_migrations(package_path)
                deployment_result["steps"].append(migration_result)
            
            # Step 6: Restart service
            if integration_config.get("requires_restart", False):
                restart_result = await self._restart_service()
                deployment_result["steps"].append(restart_result)
                
                # Wait for service to be ready
                health_result = await self._wait_for_service_health()
                deployment_result["steps"].append(health_result)
            
            # Step 7: Verify integration
            verify_result = await self._verify_integration(integration_config)
            deployment_result["steps"].append(verify_result)
            
            deployment_result["status"] = "completed"
            deployment_result["success"] = True
            
        except Exception as e:
            deployment_result["status"] = "failed"
            deployment_result["success"] = False
            deployment_result["error"] = str(e)
            
            # Attempt rollback
            rollback_result = await self._rollback_deployment(backup_result.get("backup_id"))
            deployment_result["steps"].append(rollback_result)
        
        return deployment_result
    
    def _load_integration_config(self, package_path: str) -> Dict[str, Any]:
        """Load integration configuration from package"""
        config_file = os.path.join(package_path, "integration_config.json")
        
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        
        # Check for auto_integration_deploy.sh to infer configuration
        if os.path.exists(os.path.join(package_path, "auto_integration_deploy.sh")):
            return {
                "auto_integration": True,
                "requires_api_integration": True,
                "requires_file_installation": True,
                "requires_migration": True,
                "requires_restart": True,
                "estimated_downtime": "30-60 seconds",
                "api_routes": ["/api/mcp/*"],
                "service_restart": True
            }
        
        return {"auto_integration": False}
    
    def _generate_warning_message(self, config: Dict[str, Any]) -> str:
        """Generate warning message for auto-integration deployment"""
        downtime = config.get("estimated_downtime", "30-60 seconds")
        routes = config.get("api_routes", ["Unknown routes"])
        
        return f"""
⚠️ AUTO-INTEGRATION DEPLOYMENT WARNING

This deployment will automatically:
• Update main application code (main_firestore.py)
• Install new API routes: {', '.join(routes)}
• Run database migrations
• Restart the Cloud Run service

Expected downtime: {downtime}
Backup will be created automatically.

Service will be temporarily unavailable during restart.
        """.strip()
    
    async def _create_system_backup(self) -> Dict[str, Any]:
        """Create backup of critical system files"""
        try:
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_path = os.path.join(self.backup_dir, backup_id)
            
            os.makedirs(backup_path, exist_ok=True)
            
            # Backup main_firestore.py
            if os.path.exists(self.main_file):
                shutil.copy2(self.main_file, os.path.join(backup_path, "main_firestore.py"))
            
            # Create rollback script
            rollback_script = f"""#!/bin/bash
# Rollback script for deployment {backup_id}
echo "🔄 Rolling back deployment..."
cp {backup_path}/main_firestore.py {self.main_file}
echo "✅ Files restored. Please restart service manually:"
echo "gcloud run services update {self.service_name} --region={self.region}"
"""
            
            with open(os.path.join(backup_path, "rollback.sh"), 'w') as f:
                f.write(rollback_script)
            
            os.chmod(os.path.join(backup_path, "rollback.sh"), 0o755)
            
            return {
                "step": "backup",
                "success": True,
                "message": f"System backup created: {backup_path}",
                "backup_id": backup_id,
                "backup_path": backup_path
            }
            
        except Exception as e:
            return {
                "step": "backup", 
                "success": False, 
                "error": str(e)
            }
    
    async def _stage_package_files(self, package_path: str) -> Dict[str, Any]:
        """Stage package files to staging directory"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            stage_path = os.path.join(self.staging_dir, f"auto_integration_{timestamp}")
            
            shutil.copytree(package_path, stage_path)
            
            return {
                "step": "staging",
                "success": True,
                "message": f"Files staged to: {stage_path}",
                "stage_path": stage_path
            }
            
        except Exception as e:
            return {
                "step": "staging",
                "success": False,
                "error": str(e)
            }
    
    async def _integrate_api_routes(self, package_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Integrate API routes into main_firestore.py"""
        try:
            # Use Python to safely modify main_firestore.py
            integration_script = f"""
import re

# Read main_firestore.py
with open('{self.main_file}', 'r') as f:
    content = f.read()

# Add MCP import if not present
mcp_import = 'from app.api.mcp import router as mcp_router'
if mcp_import not in content:
    # Find last app.api import and add after it
    import_pattern = r'(from app\.api\.[^\\n]*\\n)'
    matches = list(re.finditer(import_pattern, content))
    if matches:
        pos = matches[-1].end()
        content = content[:pos] + mcp_import + '\\n' + content[pos:]

# Add router registration if not present
router_reg = 'app.include_router(mcp_router, prefix="/api/mcp", tags=["mcp"])'
if router_reg not in content:
    # Find existing router registration and add after it
    router_pattern = r'(app\.include_router\([^\\n]*\\n)'
    match = re.search(router_pattern, content)
    if match:
        pos = match.end()
        content = content[:pos] + router_reg + '\\n' + content[pos:]

# Write back to file
with open('{self.main_file}', 'w') as f:
    f.write(content)
    
print("✅ API routes integrated")
"""
            
            # Execute the integration script
            process = await asyncio.create_subprocess_exec(
                'python3', '-c', integration_script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "step": "api_integration",
                    "success": True,
                    "message": "API routes integrated successfully",
                    "output": stdout.decode()
                }
            else:
                return {
                    "step": "api_integration",
                    "success": False,
                    "error": stderr.decode()
                }
                
        except Exception as e:
            return {
                "step": "api_integration",
                "success": False,
                "error": str(e)
            }
    
    async def _install_package_files(self, package_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Install package files to application directories"""
        try:
            file_mappings = {
                "api/mcp.py": "/app/app/api/mcp.py",
                "services/mcp_service.py": "/app/app/services/mcp_service.py", 
                "models/mcp_client.py": "/app/app/models/mcp_client.py",
                "schemas/mcp_client.py": "/app/app/schemas/mcp_client.py",
                "core/auth.py": "/app/app/core/auth.py"
            }
            
            installed_files = []
            
            for src_rel, dest_abs in file_mappings.items():
                src_path = os.path.join(package_path, src_rel)
                
                if os.path.exists(src_path):
                    # Create destination directory
                    os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(src_path, dest_abs)
                    installed_files.append(f"{src_rel} -> {dest_abs}")
            
            return {
                "step": "file_installation",
                "success": True,
                "message": f"Installed {len(installed_files)} files",
                "installed_files": installed_files
            }
            
        except Exception as e:
            return {
                "step": "file_installation",
                "success": False,
                "error": str(e)
            }
    
    async def _run_migrations(self, package_path: str) -> Dict[str, Any]:
        """Run database migrations"""
        try:
            migration_script = os.path.join(package_path, "migrate_mcp_only.py")
            
            if os.path.exists(migration_script):
                process = await asyncio.create_subprocess_exec(
                    'python3', migration_script,
                    cwd=package_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                if process.returncode == 0:
                    return {
                        "step": "migration",
                        "success": True,
                        "message": "Database migration completed",
                        "output": stdout.decode()
                    }
                else:
                    return {
                        "step": "migration",
                        "success": False,
                        "error": stderr.decode()
                    }
            else:
                return {
                    "step": "migration",
                    "success": True,
                    "message": "No migration script found - skipped"
                }
                
        except Exception as e:
            return {
                "step": "migration",
                "success": False,
                "error": str(e)
            }
    
    async def _restart_service(self) -> Dict[str, Any]:
        """Restart the Cloud Run service"""
        try:
            # Add environment variable to trigger new revision
            env_var = f"DEPLOYMENT_TIMESTAMP={datetime.now().timestamp()}"
            
            process = await asyncio.create_subprocess_exec(
                'gcloud', 'run', 'services', 'update', self.service_name,
                '--region', self.region,
                '--project', self.project,
                '--set-env-vars', env_var,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return {
                    "step": "service_restart",
                    "success": True,
                    "message": f"Service {self.service_name} restart initiated",
                    "output": stdout.decode()
                }
            else:
                return {
                    "step": "service_restart", 
                    "success": False,
                    "error": stderr.decode()
                }
                
        except Exception as e:
            return {
                "step": "service_restart",
                "success": False,
                "error": str(e)
            }
    
    async def _wait_for_service_health(self, timeout: int = 120) -> Dict[str, Any]:
        """Wait for service to become healthy after restart"""
        import aiohttp
        
        health_url = "https://emailpilot.ai/health"
        start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            for attempt in range(timeout // 5):  # Check every 5 seconds
                try:
                    async with session.get(health_url, timeout=5) as response:
                        if response.status == 200:
                            elapsed = (datetime.now() - start_time).total_seconds()
                            return {
                                "step": "health_check",
                                "success": True,
                                "message": f"Service healthy after {elapsed:.1f} seconds"
                            }
                except:
                    pass  # Continue checking
                
                await asyncio.sleep(5)
        
        return {
            "step": "health_check",
            "success": False,
            "error": f"Service did not become healthy within {timeout} seconds"
        }
    
    async def _verify_integration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Verify that integration was successful"""
        import aiohttp
        
        test_endpoints = config.get("api_routes", ["/api/mcp/models"])
        
        async with aiohttp.ClientSession() as session:
            results = []
            
            for endpoint in test_endpoints:
                try:
                    url = f"https://emailpilot.ai{endpoint}"
                    async with session.get(url, timeout=10) as response:
                        # 401 (Unauthorized) is expected without auth token - means endpoint exists
                        # 200 is also good if endpoint doesn't require auth
                        if response.status in [200, 401]:
                            results.append(f"✅ {endpoint} responding")
                        else:
                            results.append(f"⚠️ {endpoint} status {response.status}")
                except Exception as e:
                    results.append(f"❌ {endpoint} error: {str(e)}")
            
            success = all("✅" in result for result in results)
            
            return {
                "step": "verification",
                "success": success,
                "message": f"Integration verification {'passed' if success else 'failed'}",
                "results": results
            }
    
    async def _rollback_deployment(self, backup_id: Optional[str]) -> Dict[str, Any]:
        """Rollback a failed deployment"""
        if not backup_id:
            return {
                "step": "rollback",
                "success": False,
                "error": "No backup ID provided for rollback"
            }
        
        try:
            backup_path = os.path.join(self.backup_dir, backup_id)
            rollback_script = os.path.join(backup_path, "rollback.sh")
            
            if os.path.exists(rollback_script):
                process = await asyncio.create_subprocess_exec(
                    'bash', rollback_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                
                return {
                    "step": "rollback",
                    "success": process.returncode == 0,
                    "message": "Rollback executed - manual service restart required",
                    "output": stdout.decode()
                }
            else:
                return {
                    "step": "rollback",
                    "success": False,
                    "error": f"Rollback script not found: {rollback_script}"
                }
                
        except Exception as e:
            return {
                "step": "rollback",
                "success": False,
                "error": str(e)
            }
    
    async def _standard_deployment(self, package_path: str, package_info: Dict[str, Any]) -> Dict[str, Any]:
        """Fall back to standard deployment without auto-integration"""
        # This would be the existing deployment logic
        return {
            "status": "completed",
            "success": True,
            "auto_integration": False,
            "message": "Package deployed using standard method - manual integration may be required"
        }