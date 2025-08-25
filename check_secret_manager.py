#!/usr/bin/env python3
"""
Secret Manager Diagnostic Script
Checks permissions, connectivity, and provides troubleshooting guidance.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class SecretManagerDiagnostic:
    """Comprehensive Secret Manager diagnostic tool."""
    
    def __init__(self):
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.results = {
            "timestamp": datetime.utcnow().isoformat(),
            "project_id": self.project_id,
            "tests": {},
            "recommendations": [],
            "errors": []
        }
        
    def run_diagnostics(self) -> Dict:
        """Run all diagnostic tests and return comprehensive results."""
        print("🔍 Running Secret Manager Diagnostic Tests...")
        print("=" * 60)
        
        # Test 1: Environment variables
        self._test_environment()
        
        # Test 2: Authentication
        self._test_authentication()
        
        # Test 3: Project access
        self._test_project_access()
        
        # Test 4: Secret Manager API access
        self._test_secret_manager_api()
        
        # Test 5: Permission levels
        self._test_permissions()
        
        # Test 6: Create test secret
        self._test_create_secret()
        
        # Test 7: List existing secrets
        self._test_list_secrets()
        
        # Generate recommendations
        self._generate_recommendations()
        
        # Print summary
        self._print_summary()
        
        return self.results
    
    def _test_environment(self):
        """Test environment variable setup."""
        print("\n1. 🔧 Environment Variables")
        test_name = "environment_variables"
        
        checks = {
            "GOOGLE_CLOUD_PROJECT": self.project_id,
            "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            "SECRET_MANAGER_ENABLED": os.getenv("SECRET_MANAGER_ENABLED", "True"),
        }
        
        self.results["tests"][test_name] = {
            "status": "success",
            "details": checks,
            "issues": []
        }
        
        for var, value in checks.items():
            if value:
                print(f"   ✅ {var}: {value}")
            else:
                print(f"   ❌ {var}: Not set")
                self.results["tests"][test_name]["issues"].append(f"{var} not set")
                if var == "GOOGLE_CLOUD_PROJECT":
                    self.results["tests"][test_name]["status"] = "critical"
                else:
                    self.results["tests"][test_name]["status"] = "warning"
    
    def _test_authentication(self):
        """Test Google Cloud authentication."""
        print("\n2. 🔐 Authentication")
        test_name = "authentication"
        
        try:
            from google.auth import default
            from google.auth.exceptions import DefaultCredentialsError
            
            try:
                credentials, auth_project = default()
                print(f"   ✅ Authentication successful")
                print(f"   📋 Project from auth: {auth_project}")
                print(f"   🔑 Credential type: {type(credentials).__name__}")
                
                self.results["tests"][test_name] = {
                    "status": "success",
                    "auth_project": auth_project,
                    "credential_type": type(credentials).__name__,
                    "issues": []
                }
                
                if auth_project != self.project_id:
                    issue = f"Auth project ({auth_project}) differs from GOOGLE_CLOUD_PROJECT ({self.project_id})"
                    print(f"   ⚠️  {issue}")
                    self.results["tests"][test_name]["issues"].append(issue)
                    self.results["tests"][test_name]["status"] = "warning"
                    
            except DefaultCredentialsError as e:
                print(f"   ❌ Authentication failed: {e}")
                self.results["tests"][test_name] = {
                    "status": "critical",
                    "error": str(e),
                    "issues": ["No valid credentials found"]
                }
                
        except ImportError as e:
            print(f"   ❌ Google Auth library not available: {e}")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": str(e),
                "issues": ["Google Auth library not installed"]
            }
    
    def _test_project_access(self):
        """Test project-level access."""
        print("\n3. 🏗️  Project Access")
        test_name = "project_access"
        
        if not self.project_id:
            print("   ❌ Cannot test project access - GOOGLE_CLOUD_PROJECT not set")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": "GOOGLE_CLOUD_PROJECT not set",
                "issues": ["Project ID required"]
            }
            return
        
        try:
            from google.cloud import resourcemanager_v1
            
            client = resourcemanager_v1.ProjectsClient()
            project_name = f"projects/{self.project_id}"
            
            try:
                project = client.get_project(request={"name": project_name})
                print(f"   ✅ Project access confirmed")
                print(f"   📋 Project name: {project.display_name}")
                print(f"   🏷️  Project state: {project.state}")
                
                self.results["tests"][test_name] = {
                    "status": "success",
                    "project_name": project.display_name,
                    "project_state": str(project.state),
                    "issues": []
                }
                
            except Exception as e:
                print(f"   ❌ Project access failed: {e}")
                self.results["tests"][test_name] = {
                    "status": "error",
                    "error": str(e),
                    "issues": ["Cannot access project"]
                }
                
        except ImportError as e:
            print(f"   ⚠️  Resource Manager library not available, skipping: {e}")
            self.results["tests"][test_name] = {
                "status": "skipped",
                "reason": "Resource Manager library not available"
            }
    
    def _test_secret_manager_api(self):
        """Test Secret Manager API connectivity."""
        print("\n4. 🔒 Secret Manager API")
        test_name = "secret_manager_api"
        
        try:
            from google.cloud import secretmanager_v1
            from google.api_core import exceptions
            
            client = secretmanager_v1.SecretManagerServiceClient()
            parent = f"projects/{self.project_id}"
            
            try:
                # Try to list secrets (this tests basic API access)
                response = client.list_secrets(request={"parent": parent, "page_size": 1})
                secrets = list(response)
                
                print(f"   ✅ Secret Manager API accessible")
                print(f"   📊 Found {len(secrets)} secret(s) (showing max 1)")
                
                self.results["tests"][test_name] = {
                    "status": "success",
                    "secret_count_sample": len(secrets),
                    "issues": []
                }
                
            except exceptions.PermissionDenied as e:
                print(f"   ❌ Permission denied: {e}")
                self.results["tests"][test_name] = {
                    "status": "critical",
                    "error": str(e),
                    "issues": ["Permission denied for Secret Manager API"]
                }
                
            except Exception as e:
                print(f"   ❌ API access failed: {e}")
                self.results["tests"][test_name] = {
                    "status": "error",
                    "error": str(e),
                    "issues": ["Cannot access Secret Manager API"]
                }
                
        except ImportError as e:
            print(f"   ❌ Secret Manager library not available: {e}")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": str(e),
                "issues": ["Secret Manager library not installed"]
            }
    
    def _test_permissions(self):
        """Test specific IAM permissions."""
        print("\n5. 🛡️  Permission Analysis")
        test_name = "permissions"
        
        required_permissions = [
            "secretmanager.secrets.create",
            "secretmanager.secrets.get",
            "secretmanager.secrets.list",
            "secretmanager.versions.add",
            "secretmanager.versions.access"
        ]
        
        try:
            from google.cloud import secretmanager_v1
            from google.iam.v1 import iam_policy_pb2
            
            client = secretmanager_v1.SecretManagerServiceClient()
            resource = f"projects/{self.project_id}"
            
            try:
                # Test permissions using testIamPermissions
                request = iam_policy_pb2.TestIamPermissionsRequest(
                    resource=resource,
                    permissions=required_permissions
                )
                
                # Note: This might not work for all setups, so we'll catch exceptions
                response = client.test_iam_permissions(request=request)
                granted_permissions = list(response.permissions)
                
                print(f"   📋 Permission check results:")
                permission_results = {}
                
                for perm in required_permissions:
                    if perm in granted_permissions:
                        print(f"   ✅ {perm}")
                        permission_results[perm] = True
                    else:
                        print(f"   ❌ {perm}")
                        permission_results[perm] = False
                
                missing = [p for p in required_permissions if p not in granted_permissions]
                
                self.results["tests"][test_name] = {
                    "status": "success" if not missing else "warning",
                    "permissions": permission_results,
                    "missing_permissions": missing,
                    "issues": [f"Missing permission: {p}" for p in missing]
                }
                
            except Exception as e:
                print(f"   ⚠️  Permission test failed (this is often normal): {e}")
                self.results["tests"][test_name] = {
                    "status": "skipped",
                    "reason": f"Permission test not available: {str(e)}"
                }
                
        except ImportError:
            print(f"   ⚠️  IAM library not available, skipping permission test")
            self.results["tests"][test_name] = {
                "status": "skipped",
                "reason": "IAM library not available"
            }
    
    def _test_create_secret(self):
        """Test creating a test secret."""
        print("\n6. 🧪 Test Secret Creation")
        test_name = "create_secret"
        
        if not self.project_id:
            print("   ❌ Cannot test secret creation - GOOGLE_CLOUD_PROJECT not set")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": "GOOGLE_CLOUD_PROJECT not set",
                "issues": ["Project ID required for secret creation"]
            }
            return
        
        test_secret_name = f"emailpilot-diagnostic-test-{int(datetime.utcnow().timestamp())}"
        test_secret_value = "diagnostic-test-value"
        
        try:
            from app.services.secrets import SecretManagerService
            
            service = SecretManagerService(self.project_id)
            
            try:
                # Try to create a test secret
                service.create_secret(test_secret_name, test_secret_value, {
                    "type": "diagnostic_test",
                    "created_by": "secret_manager_diagnostic"
                })
                
                print(f"   ✅ Successfully created test secret: {test_secret_name}")
                
                # Try to read it back
                retrieved_value = service.get_secret(test_secret_name)
                if retrieved_value == test_secret_value:
                    print(f"   ✅ Successfully retrieved test secret")
                    
                    self.results["tests"][test_name] = {
                        "status": "success",
                        "test_secret_name": test_secret_name,
                        "create_success": True,
                        "retrieve_success": True,
                        "issues": []
                    }
                else:
                    print(f"   ⚠️  Retrieved value doesn't match")
                    self.results["tests"][test_name] = {
                        "status": "warning",
                        "test_secret_name": test_secret_name,
                        "create_success": True,
                        "retrieve_success": False,
                        "issues": ["Retrieved value doesn't match created value"]
                    }
                
                # Clean up test secret
                try:
                    service.delete_secret(test_secret_name)
                    print(f"   🗑️  Cleaned up test secret")
                except Exception as cleanup_error:
                    print(f"   ⚠️  Could not clean up test secret: {cleanup_error}")
                
            except Exception as e:
                print(f"   ❌ Failed to create test secret: {e}")
                self.results["tests"][test_name] = {
                    "status": "critical",
                    "error": str(e),
                    "issues": ["Cannot create secrets"]
                }
                
        except ImportError as e:
            print(f"   ❌ SecretManagerService not available: {e}")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": str(e),
                "issues": ["SecretManagerService not importable"]
            }
    
    def _test_list_secrets(self):
        """Test listing existing secrets."""
        print("\n7. 📋 Existing Secrets")
        test_name = "list_secrets"
        
        if not self.project_id:
            print("   ❌ Cannot test secret listing - GOOGLE_CLOUD_PROJECT not set")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": "GOOGLE_CLOUD_PROJECT not set",
                "issues": ["Project ID required for listing secrets"]
            }
            return
        
        try:
            from app.services.secrets import SecretManagerService
            
            service = SecretManagerService(self.project_id)
            
            try:
                secrets = service.list_secrets()
                print(f"   📊 Found {len(secrets)} existing secrets")
                
                # Look for EmailPilot-related secrets
                emailpilot_secrets = [s for s in secrets if 'emailpilot' in s.lower() or 'klaviyo' in s.lower()]
                if emailpilot_secrets:
                    print(f"   🎯 EmailPilot-related secrets ({len(emailpilot_secrets)}):")
                    for secret in sorted(emailpilot_secrets)[:10]:  # Show max 10
                        print(f"      - {secret}")
                    if len(emailpilot_secrets) > 10:
                        print(f"      ... and {len(emailpilot_secrets) - 10} more")
                
                self.results["tests"][test_name] = {
                    "status": "success",
                    "total_secrets": len(secrets),
                    "emailpilot_secrets": len(emailpilot_secrets),
                    "sample_secrets": emailpilot_secrets[:5],  # Store sample
                    "issues": []
                }
                
            except Exception as e:
                print(f"   ❌ Failed to list secrets: {e}")
                self.results["tests"][test_name] = {
                    "status": "error",
                    "error": str(e),
                    "issues": ["Cannot list secrets"]
                }
                
        except ImportError as e:
            print(f"   ❌ SecretManagerService not available: {e}")
            self.results["tests"][test_name] = {
                "status": "critical",
                "error": str(e),
                "issues": ["SecretManagerService not importable"]
            }
    
    def _generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []
        
        # Check for critical issues
        critical_tests = [test for test, result in self.results["tests"].items() 
                         if result.get("status") == "critical"]
        
        if critical_tests:
            recommendations.append({
                "priority": "HIGH",
                "category": "Critical Issues",
                "message": f"Critical failures in: {', '.join(critical_tests)}",
                "action": "Address these issues before proceeding"
            })
        
        # Environment setup
        env_test = self.results["tests"].get("environment_variables", {})
        if env_test.get("issues"):
            recommendations.append({
                "priority": "HIGH",
                "category": "Environment",
                "message": "Set missing environment variables",
                "action": "export GOOGLE_CLOUD_PROJECT=your-project-id"
            })
        
        # Authentication
        auth_test = self.results["tests"].get("authentication", {})
        if auth_test.get("status") == "critical":
            recommendations.append({
                "priority": "HIGH",
                "category": "Authentication",
                "message": "Google Cloud authentication not configured",
                "action": "Run: gcloud auth application-default login"
            })
        
        # Permissions
        perm_test = self.results["tests"].get("permissions", {})
        if perm_test.get("missing_permissions"):
            missing = perm_test["missing_permissions"]
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Permissions",
                "message": f"Missing {len(missing)} Secret Manager permissions",
                "action": "Grant Secret Manager roles to your service account"
            })
        
        # Secret creation
        create_test = self.results["tests"].get("create_secret", {})
        if create_test.get("status") == "critical":
            recommendations.append({
                "priority": "HIGH",
                "category": "Secret Creation",
                "message": "Cannot create secrets in Secret Manager",
                "action": "Check IAM permissions for secretmanager.secrets.create"
            })
        
        self.results["recommendations"] = recommendations
    
    def _print_summary(self):
        """Print diagnostic summary."""
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 60)
        
        # Count test results
        test_counts = {"success": 0, "warning": 0, "error": 0, "critical": 0, "skipped": 0}
        for test_result in self.results["tests"].values():
            status = test_result.get("status", "unknown")
            test_counts[status] = test_counts.get(status, 0) + 1
        
        print(f"✅ Successful: {test_counts['success']}")
        print(f"⚠️  Warnings: {test_counts['warning']}")
        print(f"❌ Errors: {test_counts['error']}")
        print(f"🚨 Critical: {test_counts['critical']}")
        print(f"⏭️  Skipped: {test_counts['skipped']}")
        
        # Print recommendations
        if self.results["recommendations"]:
            print(f"\n🎯 RECOMMENDATIONS ({len(self.results['recommendations'])})")
            print("-" * 40)
            for i, rec in enumerate(self.results["recommendations"], 1):
                priority = rec["priority"]
                icon = "🚨" if priority == "HIGH" else "⚠️" if priority == "MEDIUM" else "💡"
                print(f"{i}. {icon} [{priority}] {rec['category']}")
                print(f"   Issue: {rec['message']}")
                print(f"   Action: {rec['action']}")
                print()
        
        # Overall status
        if test_counts["critical"] > 0:
            print("🚨 OVERALL STATUS: CRITICAL - Secret Manager cannot be used")
        elif test_counts["error"] > 0:
            print("❌ OVERALL STATUS: ERROR - Secret Manager may work with issues")
        elif test_counts["warning"] > 0:
            print("⚠️  OVERALL STATUS: WARNING - Secret Manager should work")
        else:
            print("✅ OVERALL STATUS: SUCCESS - Secret Manager is properly configured")

def print_troubleshooting_guide():
    """Print comprehensive troubleshooting guide."""
    print("\n" + "=" * 60)
    print("🛠️  TROUBLESHOOTING GUIDE")
    print("=" * 60)
    
    guide = [
        {
            "issue": "GOOGLE_CLOUD_PROJECT not set",
            "solutions": [
                "export GOOGLE_CLOUD_PROJECT=your-project-id",
                "Add to .env file: GOOGLE_CLOUD_PROJECT=your-project-id",
                "Set in your deployment environment"
            ]
        },
        {
            "issue": "Authentication failed",
            "solutions": [
                "gcloud auth application-default login",
                "Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json",
                "For Cloud Run: ensure service account has proper roles",
                "For local development: use gcloud auth login"
            ]
        },
        {
            "issue": "Permission denied for Secret Manager",
            "solutions": [
                "Grant 'Secret Manager Admin' role to your service account",
                "Or grant specific roles: secretmanager.secretAccessor, secretmanager.secretVersionManager",
                "gcloud projects add-iam-policy-binding PROJECT_ID --member='serviceAccount:EMAIL' --role='roles/secretmanager.admin'",
                "Check if Secret Manager API is enabled: gcloud services enable secretmanager.googleapis.com"
            ]
        },
        {
            "issue": "Cannot create secrets",
            "solutions": [
                "Check if you have secretmanager.secrets.create permission",
                "Ensure Secret Manager API is enabled in your project",
                "Verify billing is enabled for the project",
                "Check quotas: https://console.cloud.google.com/iam-admin/quotas"
            ]
        },
        {
            "issue": "Development environment setup",
            "solutions": [
                "Use Firestore emulator for local development",
                "Set SECRET_MANAGER_ENABLED=false for local testing",
                "Use environment variables as fallback",
                "Consider using .env file for local secrets (not for production)"
            ]
        }
    ]
    
    for i, item in enumerate(guide, 1):
        print(f"{i}. {item['issue']}")
        for j, solution in enumerate(item['solutions'], 1):
            print(f"   {j}. {solution}")
        print()

def main():
    """Main diagnostic function."""
    print("🔍 EmailPilot Secret Manager Diagnostic Tool")
    print("=" * 60)
    print("This tool will check your Secret Manager configuration and permissions.")
    print("It will create and delete a test secret during the process.")
    print()
    
    # Run diagnostics
    diagnostic = SecretManagerDiagnostic()
    results = diagnostic.run_diagnostics()
    
    # Print troubleshooting guide
    print_troubleshooting_guide()
    
    # Save results to file
    results_file = "secret_manager_diagnostic_results.json"
    try:
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Diagnostic results saved to: {results_file}")
    except Exception as e:
        print(f"\n⚠️  Could not save results file: {e}")
    
    # Exit with appropriate code
    critical_issues = sum(1 for test in results["tests"].values() if test.get("status") == "critical")
    if critical_issues > 0:
        print(f"\n🚨 Exiting with error code due to {critical_issues} critical issue(s)")
        sys.exit(1)
    else:
        print(f"\n✅ Diagnostic completed successfully")
        sys.exit(0)

if __name__ == "__main__":
    main()