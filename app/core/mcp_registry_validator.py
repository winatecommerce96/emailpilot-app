"""
MCP Registry Validator

Validates that the Universal MCP Registry is properly configured and enforced.
Run this at startup to ensure the system is working correctly.
"""
import logging
from typing import Dict, Any, List
import os
import sys
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPRegistryValidator:
    """
    Validates the Universal MCP Registry setup and enforcement
    """
    
    @classmethod
    def validate_all(cls) -> Dict[str, Any]:
        """
        Run all validation checks
        
        Returns:
            Validation report with pass/fail status
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'passed': True,
            'enforcement_active': False
        }
        
        # Check 1: Enforcement module exists
        try:
            from app.core.mcp_enforcement import MCPRegistryEnforcement
            report['checks'].append({
                'name': 'Enforcement Module',
                'status': 'PASS',
                'message': 'MCP enforcement module loaded successfully'
            })
        except ImportError as e:
            report['checks'].append({
                'name': 'Enforcement Module',
                'status': 'FAIL',
                'message': f'Cannot load enforcement module: {e}'
            })
            report['passed'] = False
        
        # Check 2: Registry module exists
        try:
            from app.services.universal_mcp_registry import UniversalMCPRegistry
            report['checks'].append({
                'name': 'Registry Module',
                'status': 'PASS',
                'message': 'Universal MCP Registry loaded successfully'
            })
        except ImportError as e:
            report['checks'].append({
                'name': 'Registry Module',
                'status': 'FAIL',
                'message': f'Cannot load registry module: {e}'
            })
            report['passed'] = False
        
        # Check 3: API endpoints registered
        try:
            from app.api.mcp_management import router
            report['checks'].append({
                'name': 'API Endpoints',
                'status': 'PASS',
                'message': 'MCP management API endpoints available'
            })
        except ImportError as e:
            report['checks'].append({
                'name': 'API Endpoints',
                'status': 'FAIL',
                'message': f'Cannot load API endpoints: {e}'
            })
            report['passed'] = False
        
        # Check 4: Enforcement is active
        if os.environ.get('MCP_REGISTRY_ENFORCED') == 'true':
            report['enforcement_active'] = True
            report['checks'].append({
                'name': 'Enforcement Status',
                'status': 'PASS',
                'message': 'MCP Registry enforcement is ACTIVE'
            })
        else:
            report['checks'].append({
                'name': 'Enforcement Status',
                'status': 'WARNING',
                'message': 'MCP Registry enforcement not yet activated'
            })
        
        # Check 5: LLM Selector available
        try:
            from app.services.llm_selector import LLMSelector
            selector = LLMSelector()
            models = selector.list_models()
            report['checks'].append({
                'name': 'LLM Selector',
                'status': 'PASS',
                'message': f'LLM Selector ready with {len(models)} models'
            })
        except Exception as e:
            report['checks'].append({
                'name': 'LLM Selector',
                'status': 'WARNING',
                'message': f'LLM Selector issue: {e}'
            })
        
        # Check 6: Check for bypass attempts
        bypass_files = cls._check_for_bypass_files()
        if bypass_files:
            report['checks'].append({
                'name': 'Bypass Detection',
                'status': 'WARNING',
                'message': f'Found {len(bypass_files)} files that may bypass registry',
                'files': bypass_files
            })
        else:
            report['checks'].append({
                'name': 'Bypass Detection',
                'status': 'PASS',
                'message': 'No bypass attempts detected'
            })
        
        # Check 7: Documentation exists
        docs = [
            'SMART_MCP_GATEWAY.md',
            'DEVELOPER_MCP_GUIDE.md'
        ]
        missing_docs = []
        for doc in docs:
            if not os.path.exists(doc):
                missing_docs.append(doc)
        
        if missing_docs:
            report['checks'].append({
                'name': 'Documentation',
                'status': 'WARNING',
                'message': f'Missing docs: {missing_docs}'
            })
        else:
            report['checks'].append({
                'name': 'Documentation',
                'status': 'PASS',
                'message': 'All documentation present'
            })
        
        # Generate summary
        failed = sum(1 for check in report['checks'] if check['status'] == 'FAIL')
        warnings = sum(1 for check in report['checks'] if check['status'] == 'WARNING')
        passed = sum(1 for check in report['checks'] if check['status'] == 'PASS')
        
        report['summary'] = {
            'total_checks': len(report['checks']),
            'passed': passed,
            'warnings': warnings,
            'failed': failed
        }
        
        # Print report
        cls._print_report(report)
        
        return report
    
    @classmethod
    def _check_for_bypass_files(cls) -> List[str]:
        """
        Check for files that might bypass the registry
        
        Returns:
            List of suspicious files
        """
        suspicious = []
        api_dir = 'app/api'
        
        if os.path.exists(api_dir):
            for file in os.listdir(api_dir):
                if file.startswith('mcp_') and file not in [
                    'mcp_management.py',
                    'mcp_registry.py',
                    'mcp_klaviyo.py',  # Legacy, being migrated
                    'mcp_local.py',    # Legacy, being migrated
                    'mcp_chat.py',     # UI interface, allowed
                ]:
                    # Check if file was created recently
                    filepath = os.path.join(api_dir, file)
                    if os.path.exists(filepath):
                        stat = os.stat(filepath)
                        # If created in last 7 days, flag it
                        age_days = (datetime.now().timestamp() - stat.st_mtime) / 86400
                        if age_days < 7:
                            suspicious.append(file)
        
        return suspicious
    
    @classmethod
    def _print_report(cls, report: Dict[str, Any]):
        """
        Print validation report to console
        """
        print("\n" + "=" * 80)
        print("🔍 MCP REGISTRY VALIDATION REPORT")
        print("=" * 80)
        
        for check in report['checks']:
            status_emoji = {
                'PASS': '✅',
                'WARNING': '⚠️',
                'FAIL': '❌'
            }.get(check['status'], '❔')
            
            print(f"{status_emoji} {check['name']}: {check['message']}")
            if 'files' in check:
                for file in check['files']:
                    print(f"    - {file}")
        
        print("\n" + "-" * 80)
        summary = report['summary']
        print(f"Summary: {summary['passed']} passed, "
              f"{summary['warnings']} warnings, {summary['failed']} failed")
        
        if report['enforcement_active']:
            print("🔒 ENFORCEMENT: ACTIVE - All new MCPs must use the registry")
        else:
            print("⚠️ ENFORCEMENT: NOT ACTIVE - Run enforce_mcp_registry()")
        
        if report['passed']:
            print("✅ OVERALL: MCP Registry system is properly configured")
        else:
            print("❌ OVERALL: MCP Registry system has issues that need fixing")
        
        print("=" * 80 + "\n")


def validate_mcp_registry() -> bool:
    """
    Quick validation function for startup
    
    Returns:
        True if validation passes, False otherwise
    """
    report = MCPRegistryValidator.validate_all()
    return report['passed'] and report['summary']['failed'] == 0


if __name__ == "__main__":
    # Run validation when executed directly
    sys.exit(0 if validate_mcp_registry() else 1)