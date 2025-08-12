#!/usr/bin/env python3
"""
EmailPilot SPA Compatibility Checker
Validates that the calendar SPA deployment package is compatible with the existing EmailPilot architecture
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SPACompatibilityChecker:
    def __init__(self, emailpilot_root: str):
        self.emailpilot_root = Path(emailpilot_root)
        self.compatibility_report = {
            "compatible": True,
            "warnings": [],
            "errors": [],
            "recommendations": [],
            "checks_performed": []
        }
    
    def check_all(self) -> Dict[str, Any]:
        """Run all compatibility checks"""
        logger.info("🔍 Starting EmailPilot SPA compatibility check...")
        
        # Core architecture checks
        self.check_spa_structure()
        self.check_react_components()
        self.check_api_structure()
        self.check_database_compatibility()
        
        # Integration point checks
        self.check_existing_calendar()
        self.check_goals_system()
        self.check_component_loading()
        
        # Frontend checks
        self.check_javascript_compatibility()
        self.check_styling_compatibility()
        
        # Backend checks
        self.check_fastapi_compatibility()
        self.check_route_structure()
        
        # Generate final report
        self.generate_compatibility_report()
        
        return self.compatibility_report
    
    def check_spa_structure(self):
        """Check if EmailPilot has proper SPA structure"""
        check_name = "SPA Structure Validation"
        self.compatibility_report["checks_performed"].append(check_name)
        
        required_files = [
            "frontend/public/index.html",
            "frontend/public/app.js",
            "main.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            full_path = self.emailpilot_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.compatibility_report["errors"].append(
                f"Missing core SPA files: {', '.join(missing_files)}"
            )
            self.compatibility_report["compatible"] = False
        else:
            logger.info("✅ SPA structure is valid")
    
    def check_react_components(self):
        """Check React component loading system"""
        check_name = "React Component System"
        self.compatibility_report["checks_performed"].append(check_name)
        
        index_html = self.emailpilot_root / "frontend/public/index.html"
        if not index_html.exists():
            self.compatibility_report["errors"].append("index.html not found")
            return
        
        content = index_html.read_text()
        
        # Check for React dependencies
        react_checks = [
            "react@17",
            "react-dom@17",
            "@babel/standalone"
        ]
        
        missing_react = []
        for check in react_checks:
            if check not in content:
                missing_react.append(check)
        
        if missing_react:
            self.compatibility_report["warnings"].append(
                f"Missing React dependencies: {', '.join(missing_react)}"
            )
        
        # Check for component loading structure
        if "components/" not in content:
            self.compatibility_report["warnings"].append(
                "Component loading structure may be incomplete"
            )
        
        logger.info("✅ React component system check completed")
    
    def check_existing_calendar(self):
        """Check existing calendar integration"""
        check_name = "Existing Calendar Integration"
        self.compatibility_report["checks_performed"].append(check_name)
        
        app_js = self.emailpilot_root / "frontend/public/app.js"
        if not app_js.exists():
            self.compatibility_report["errors"].append("app.js not found")
            return
        
        try:
            content = app_js.read_text()
            
            # Check for existing calendar integration
            calendar_indicators = [
                "CalendarWrapper",
                "currentView === 'calendar'",
                "Calendar",
                "calendar"
            ]
            
            found_indicators = [ind for ind in calendar_indicators if ind in content]
            
            if len(found_indicators) < 2:
                self.compatibility_report["warnings"].append(
                    "Existing calendar integration may be incomplete"
                )
            else:
                logger.info("✅ Existing calendar integration detected")
                
        except Exception as e:
            self.compatibility_report["errors"].append(f"Error reading app.js: {e}")
    
    def check_goals_system(self):
        """Check goals system compatibility"""
        check_name = "Goals System Compatibility"
        self.compatibility_report["checks_performed"].append(check_name)
        
        # Check for goals API
        goals_api = self.emailpilot_root / "app/api/goals.py"
        if not goals_api.exists():
            self.compatibility_report["warnings"].append(
                "Goals API not found - goals features may not work"
            )
        
        # Check for goals models
        goals_model = self.emailpilot_root / "app/models/goal.py"
        if not goals_model.exists():
            self.compatibility_report["warnings"].append(
                "Goals model not found - database integration may fail"
            )
        
        # Check for existing goals-calendar integration
        goals_calendar_api = self.emailpilot_root / "app/api/goals_aware_calendar.py"
        if goals_calendar_api.exists():
            logger.info("✅ Existing goals-calendar integration found")
        else:
            self.compatibility_report["recommendations"].append(
                "Consider implementing goals-calendar integration for full functionality"
            )
    
    def check_api_structure(self):
        """Check FastAPI structure compatibility"""
        check_name = "FastAPI Structure"
        self.compatibility_report["checks_performed"].append(check_name)
        
        main_py = self.emailpilot_root / "main.py"
        if not main_py.exists():
            self.compatibility_report["errors"].append("main.py not found")
            return
        
        try:
            content = main_py.read_text()
            
            # Check for FastAPI app structure
            if "app = FastAPI(" not in content:
                self.compatibility_report["errors"].append("FastAPI app structure not found")
                self.compatibility_report["compatible"] = False
                return
            
            # Check for CORS middleware
            if "CORSMiddleware" not in content:
                self.compatibility_report["warnings"].append(
                    "CORS middleware not found - API calls may fail"
                )
            
            # Check for router inclusion pattern
            if "include_router" not in content:
                self.compatibility_report["warnings"].append(
                    "Router inclusion pattern not found"
                )
            
            logger.info("✅ FastAPI structure is compatible")
            
        except Exception as e:
            self.compatibility_report["errors"].append(f"Error reading main.py: {e}")
    
    def check_component_loading(self):
        """Check component loading mechanisms"""
        check_name = "Component Loading System"
        self.compatibility_report["checks_performed"].append(check_name)
        
        components_dir = self.emailpilot_root / "frontend/public/components"
        if not components_dir.exists():
            self.compatibility_report["errors"].append(
                "Components directory not found"
            )
            self.compatibility_report["compatible"] = False
            return
        
        # Check for existing calendar components
        calendar_components = list(components_dir.glob("Calendar*.js"))
        if not calendar_components:
            self.compatibility_report["warnings"].append(
                "No existing calendar components found"
            )
        else:
            logger.info(f"✅ Found {len(calendar_components)} calendar components")
        
        # Check for component registration system
        index_html = self.emailpilot_root / "frontend/public/index.html"
        if index_html.exists():
            content = index_html.read_text()
            if "babel" in content and "components/" in content:
                logger.info("✅ Component loading system detected")
            else:
                self.compatibility_report["warnings"].append(
                    "Component loading system may need updates"
                )
    
    def check_database_compatibility(self):
        """Check database structure compatibility"""
        check_name = "Database Compatibility"
        self.compatibility_report["checks_performed"].append(check_name)
        
        # Check for database models
        models_dir = self.emailpilot_root / "app/models"
        if not models_dir.exists():
            self.compatibility_report["errors"].append("Models directory not found")
            return
        
        required_models = ["client.py", "goal.py"]
        missing_models = []
        
        for model in required_models:
            if not (models_dir / model).exists():
                missing_models.append(model)
        
        if missing_models:
            self.compatibility_report["warnings"].append(
                f"Missing models: {', '.join(missing_models)}"
            )
        else:
            logger.info("✅ Required database models found")
        
        # Check for database configuration
        db_config = self.emailpilot_root / "app/core/database.py"
        if not db_config.exists():
            self.compatibility_report["warnings"].append(
                "Database configuration not found"
            )
    
    def check_javascript_compatibility(self):
        """Check JavaScript compatibility"""
        check_name = "JavaScript Compatibility"
        self.compatibility_report["checks_performed"].append(check_name)
        
        # Check for modern JavaScript features used in components
        features_to_check = [
            "React.createElement",
            "useState",
            "useEffect",
            "window.API_BASE_URL"
        ]
        
        app_js = self.emailpilot_root / "frontend/public/app.js"
        if app_js.exists():
            content = app_js.read_text()
            
            missing_features = []
            for feature in features_to_check:
                if feature not in content:
                    missing_features.append(feature)
            
            if missing_features:
                self.compatibility_report["warnings"].append(
                    f"JavaScript features not found: {', '.join(missing_features)}"
                )
            else:
                logger.info("✅ JavaScript compatibility verified")
    
    def check_styling_compatibility(self):
        """Check styling system compatibility"""
        check_name = "Styling System"
        self.compatibility_report["checks_performed"].append(check_name)
        
        index_html = self.emailpilot_root / "frontend/public/index.html"
        if index_html.exists():
            content = index_html.read_text()
            
            if "tailwindcss" in content:
                logger.info("✅ TailwindCSS detected")
                self.compatibility_report["recommendations"].append(
                    "TailwindCSS found - calendar components will integrate seamlessly"
                )
            else:
                self.compatibility_report["warnings"].append(
                    "TailwindCSS not detected - styling may need adjustments"
                )
    
    def check_fastapi_compatibility(self):
        """Check FastAPI version and features"""
        check_name = "FastAPI Features"
        self.compatibility_report["checks_performed"].append(check_name)
        
        requirements_file = self.emailpilot_root / "requirements.txt"
        if requirements_file.exists():
            content = requirements_file.read_text()
            
            if "fastapi" in content.lower():
                logger.info("✅ FastAPI dependency found")
            else:
                self.compatibility_report["warnings"].append(
                    "FastAPI not found in requirements"
                )
        else:
            self.compatibility_report["warnings"].append(
                "requirements.txt not found"
            )
    
    def check_route_structure(self):
        """Check API route structure"""
        check_name = "API Route Structure"
        self.compatibility_report["checks_performed"].append(check_name)
        
        api_dir = self.emailpilot_root / "app/api"
        if not api_dir.exists():
            self.compatibility_report["errors"].append("API directory not found")
            return
        
        # Check for existing API files
        api_files = list(api_dir.glob("*.py"))
        if len(api_files) < 3:
            self.compatibility_report["warnings"].append(
                "Limited API structure detected"
            )
        else:
            logger.info(f"✅ Found {len(api_files)} API modules")
    
    def generate_compatibility_report(self):
        """Generate final compatibility report"""
        report = self.compatibility_report
        
        print("\n" + "="*60)
        print("📋 EMAILPILOT SPA COMPATIBILITY REPORT")
        print("="*60)
        
        # Overall compatibility status
        if report["compatible"]:
            print("✅ COMPATIBLE: Calendar SPA deployment is compatible")
        else:
            print("❌ NOT COMPATIBLE: Critical issues found")
        
        print(f"\n📊 Checks Performed: {len(report['checks_performed'])}")
        
        # Errors
        if report["errors"]:
            print(f"\n❌ Errors ({len(report['errors'])}):")
            for error in report["errors"]:
                print(f"  • {error}")
        
        # Warnings
        if report["warnings"]:
            print(f"\n⚠️ Warnings ({len(report['warnings'])}):")
            for warning in report["warnings"]:
                print(f"  • {warning}")
        
        # Recommendations
        if report["recommendations"]:
            print(f"\n💡 Recommendations ({len(report['recommendations'])}):")
            for rec in report["recommendations"]:
                print(f"  • {rec}")
        
        # Next steps
        print("\n🎯 Next Steps:")
        if report["compatible"]:
            print("  1. ✅ Deploy the calendar SPA package")
            print("  2. ✅ Follow integration instructions")
            print("  3. ✅ Test calendar functionality")
            print("  4. ✅ Monitor for any issues")
        else:
            print("  1. ❌ Fix critical errors listed above")
            print("  2. ❌ Re-run compatibility check")
            print("  3. ❌ Deploy only after compatibility confirmed")
        
        print("\n" + "="*60)

def main():
    """Main execution function"""
    if len(sys.argv) > 1:
        emailpilot_root = sys.argv[1]
    else:
        # Try to detect EmailPilot root from current location
        current_dir = Path.cwd()
        possible_roots = [
            current_dir,
            current_dir.parent,
            current_dir / "emailpilot-app",
            Path("/app")  # Production path
        ]
        
        emailpilot_root = None
        for root in possible_roots:
            if (root / "main.py").exists() and (root / "frontend").exists():
                emailpilot_root = root
                break
        
        if not emailpilot_root:
            print("❌ Could not find EmailPilot root directory")
            print("Usage: python check_spa_compatibility.py [emailpilot_root]")
            sys.exit(1)
    
    checker = SPACompatibilityChecker(str(emailpilot_root))
    report = checker.check_all()
    
    # Exit with appropriate code
    sys.exit(0 if report["compatible"] else 1)

if __name__ == "__main__":
    main()