#!/usr/bin/env python3

"""
EmailPilot Component Registration System
Automatically registers new React components in the production build
Version: 1.0.0
"""

import os
import re
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComponentRegistrar:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.frontend_dir = self.project_root / "frontend" / "public"
        self.components_dir = self.frontend_dir / "components"
        self.index_file = self.frontend_dir / "index.html"
        self.app_file = self.frontend_dir / "app.js"
        
        # Backup directory
        self.backup_dir = self.project_root / "deployments" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def create_backup(self, file_path: Path) -> Path:
        """Create a backup of a file before modification"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.backup_{timestamp}"
        backup_path = self.backup_dir / backup_name
        
        if file_path.exists():
            backup_path.write_text(file_path.read_text())
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        return None
        
    def scan_components(self) -> Dict[str, Dict]:
        """Scan components directory and extract metadata"""
        components = {}
        
        if not self.components_dir.exists():
            logger.warning(f"Components directory not found: {self.components_dir}")
            return components
            
        for component_file in self.components_dir.glob("*.js"):
            component_name = component_file.stem
            
            # Read component file and extract metadata
            content = component_file.read_text()
            
            # Extract component metadata from comments or exports
            metadata = {
                "name": component_name,
                "path": f"components/{component_file.name}",
                "requires_babel": self._requires_babel(content),
                "dependencies": self._extract_dependencies(content),
                "menu_item": self._extract_menu_config(content),
                "route_config": self._extract_route_config(content)
            }
            
            components[component_name] = metadata
            
        logger.info(f"Scanned {len(components)} components")
        return components
        
    def _requires_babel(self, content: str) -> bool:
        """Check if component requires Babel transformation"""
        jsx_patterns = [
            r'<[A-Z][^>]*>',  # JSX elements
            r'React\.',       # React usage
            r'=>\s*\(',       # Arrow functions with JSX
        ]
        
        for pattern in jsx_patterns:
            if re.search(pattern, content):
                return True
        return False
        
    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract component dependencies"""
        dependencies = []
        
        # Look for window.ComponentName usage
        window_deps = re.findall(r'window\.(\w+)', content)
        dependencies.extend(window_deps)
        
        return list(set(dependencies))
        
    def _extract_menu_config(self, content: str) -> Optional[Dict]:
        """Extract menu configuration from component comments"""
        # Look for menu configuration in comments
        menu_match = re.search(
            r'/\*\*?\s*@menu\s+({[^}]+})\s*\*/', 
            content, 
            re.MULTILINE | re.DOTALL
        )
        
        if menu_match:
            try:
                return json.loads(menu_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Invalid menu configuration JSON")
                
        return None
        
    def _extract_route_config(self, content: str) -> Optional[Dict]:
        """Extract route configuration from component comments"""
        # Look for route configuration in comments
        route_match = re.search(
            r'/\*\*?\s*@route\s+({[^}]+})\s*\*/', 
            content, 
            re.MULTILINE | re.DOTALL
        )
        
        if route_match:
            try:
                return json.loads(route_match.group(1))
            except json.JSONDecodeError:
                logger.warning("Invalid route configuration JSON")
                
        return None
        
    def register_component_in_index(self, component_name: str, component_path: str, requires_babel: bool = True) -> bool:
        """Register component in index.html"""
        if not self.index_file.exists():
            logger.error(f"Index file not found: {self.index_file}")
            return False
            
        content = self.index_file.read_text()
        
        # Check if component is already registered
        if component_path in content:
            logger.info(f"Component {component_name} already registered in index.html")
            return True
            
        # Create backup
        self.create_backup(self.index_file)
        
        # Determine script tag type
        script_type = 'type="text/babel" ' if requires_babel else ''
        script_tag = f'    <script {script_type}src="{component_path}"></script>'
        
        # Find insertion point
        if "<!-- Main App -->" in content:
            # Insert before main app
            content = content.replace(
                "    <!-- Main App -->",
                f"    <!-- {component_name} Component -->\n    {script_tag}\n    <!-- Main App -->"
            )
        elif "</body>" in content:
            # Insert before closing body tag
            content = content.replace(
                "</body>",
                f"    <!-- {component_name} Component -->\n    {script_tag}\n</body>"
            )
        else:
            logger.error("Could not find insertion point in index.html")
            return False
            
        # Write updated content
        self.index_file.write_text(content)
        logger.info(f"Registered {component_name} in index.html")
        return True
        
    def add_menu_item(self, item_id: str, item_label: str, item_icon: str = "🔧", admin_only: bool = True) -> bool:
        """Add menu item to app.js"""
        if not self.app_file.exists():
            logger.error(f"App file not found: {self.app_file}")
            return False
            
        content = self.app_file.read_text()
        
        # Check if menu item already exists
        if f"id: '{item_id}'" in content:
            logger.info(f"Menu item {item_id} already exists")
            return True
            
        # Create backup
        self.create_backup(self.app_file)
        
        if admin_only:
            # Find admin check section and add menu item
            admin_pattern = r"(if \(user\.email === 'damon@winatecommerce\.com' \|\| user\.email === 'admin@emailpilot\.ai'\) \{[^}]*menuItems\.push\(\{ id: 'admin', label: 'Admin', icon: '⚙️' \}\);)"
            
            if re.search(admin_pattern, content):
                replacement = rf"\1\n        menuItems.push({{ id: '{item_id}', label: '{item_label}', icon: '{item_icon}' }});"
                content = re.sub(admin_pattern, replacement, content)
                
                self.app_file.write_text(content)
                logger.info(f"Added admin menu item: {item_label}")
                return True
            else:
                logger.error("Could not find admin menu section")
                return False
        else:
            # Add to regular menu items
            menu_pattern = r"(const menuItems = \[[^\]]*\]);)"
            
            if re.search(menu_pattern, content):
                # This is more complex - would need to parse the array properly
                logger.warning("Regular menu item addition not implemented yet")
                return False
                
        return False
        
    def add_component_route(self, component_id: str, component_name: str) -> bool:
        """Add component route case to app.js"""
        if not self.app_file.exists():
            logger.error(f"App file not found: {self.app_file}")
            return False
            
        content = self.app_file.read_text()
        
        # Check if route already exists
        if f"case '{component_id}':" in content:
            logger.info(f"Route for {component_id} already exists")
            return True
            
        # Create backup
        self.create_backup(self.app_file)
        
        # Find the switch statement and add new case
        admin_case_pattern = r"(case 'admin':[^}]*<window\.AdminDashboard[^;]*;[^}]*break;)"
        
        if re.search(admin_case_pattern, content):
            new_case = f"""
            case '{component_id}':
                return loading ? (
                    <div className="p-8 text-center">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mb-4"></div>
                        <p className="text-sm text-gray-600">Loading {component_name}...</p>
                    </div>
                ) : window.{component_name} ? (
                    <window.{component_name} />
                ) : (
                    <div className="p-8">
                        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                            <h3 className="text-lg font-semibold text-red-800 mb-2">Component Not Available</h3>
                            <p className="text-sm text-red-700">
                                {component_name} component could not be loaded.
                            </p>
                        </div>
                    </div>
                );"""
                
            replacement = rf"\1{new_case}"
            content = re.sub(admin_case_pattern, replacement, content, flags=re.DOTALL)
            
            self.app_file.write_text(content)
            logger.info(f"Added route case for {component_id}")
            return True
        else:
            logger.error("Could not find switch statement in app.js")
            return False
            
    def register_component(self, component_name: str, **kwargs) -> bool:
        """Register a complete component with menu and routing"""
        logger.info(f"Registering component: {component_name}")
        
        # Default configuration
        config = {
            "requires_babel": True,
            "admin_only": True,
            "icon": "🔧",
            "component_id": component_name.lower().replace("management", ""),
            **kwargs
        }
        
        component_path = f"components/{component_name}.js"
        
        # 1. Register in index.html
        success = self.register_component_in_index(
            component_name, 
            component_path, 
            config["requires_babel"]
        )
        if not success:
            return False
            
        # 2. Add menu item if specified
        if "menu_label" in config:
            success = self.add_menu_item(
                config["component_id"],
                config["menu_label"],
                config["icon"],
                config["admin_only"]
            )
            if not success:
                return False
                
        # 3. Add route
        if "menu_label" in config:  # Only add route if it has a menu item
            success = self.add_component_route(
                config["component_id"],
                component_name
            )
            if not success:
                return False
                
        logger.info(f"Successfully registered component: {component_name}")
        return True
        
    def unregister_component(self, component_name: str) -> bool:
        """Remove component registration"""
        logger.info(f"Unregistering component: {component_name}")
        
        success = True
        
        # Remove from index.html
        if self.index_file.exists():
            self.create_backup(self.index_file)
            content = self.index_file.read_text()
            
            # Remove script tag and comment
            pattern = rf'    <!-- {component_name} Component -->\n    <script[^>]*src="components/{component_name}\.js"></script>\n'
            content = re.sub(pattern, '', content)
            
            self.index_file.write_text(content)
            logger.info(f"Removed {component_name} from index.html")
            
        return success
        
    def generate_registration_report(self) -> Dict:
        """Generate a report of all registered components"""
        components = self.scan_components()
        
        # Check which components are registered in index.html
        index_content = self.index_file.read_text() if self.index_file.exists() else ""
        app_content = self.app_file.read_text() if self.app_file.exists() else ""
        
        for component_name, metadata in components.items():
            metadata["registered_in_index"] = metadata["path"] in index_content
            metadata["has_menu_item"] = f"id: '{component_name.lower()}'" in app_content
            metadata["has_route"] = f"case '{component_name.lower()}':" in app_content
            
        return {
            "timestamp": datetime.now().isoformat(),
            "total_components": len(components),
            "components": components
        }


def main():
    parser = argparse.ArgumentParser(description="EmailPilot Component Registration System")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Scan command
    scan_parser = subparsers.add_parser("scan", help="Scan components directory")
    
    # Register command
    register_parser = subparsers.add_parser("register", help="Register a component")
    register_parser.add_argument("component_name", help="Component name")
    register_parser.add_argument("--menu-label", help="Menu label")
    register_parser.add_argument("--icon", default="🔧", help="Menu icon")
    register_parser.add_argument("--admin-only", action="store_true", help="Admin only menu item")
    register_parser.add_argument("--no-babel", action="store_true", help="Component doesn't need Babel")
    
    # Unregister command
    unregister_parser = subparsers.add_parser("unregister", help="Unregister a component")
    unregister_parser.add_argument("component_name", help="Component name")
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate registration report")
    report_parser.add_argument("--output", help="Output file (default: stdout)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
        
    registrar = ComponentRegistrar(args.project_root)
    
    if args.command == "scan":
        components = registrar.scan_components()
        print(json.dumps(components, indent=2))
        
    elif args.command == "register":
        config = {
            "requires_babel": not args.no_babel,
            "admin_only": args.admin_only,
            "icon": args.icon
        }
        
        if args.menu_label:
            config["menu_label"] = args.menu_label
            
        success = registrar.register_component(args.component_name, **config)
        if success:
            print(f"Successfully registered {args.component_name}")
        else:
            print(f"Failed to register {args.component_name}")
            exit(1)
            
    elif args.command == "unregister":
        success = registrar.unregister_component(args.component_name)
        if success:
            print(f"Successfully unregistered {args.component_name}")
        else:
            print(f"Failed to unregister {args.component_name}")
            exit(1)
            
    elif args.command == "report":
        report = registrar.generate_registration_report()
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"Report saved to {args.output}")
        else:
            print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()