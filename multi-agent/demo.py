#!/usr/bin/env python3
"""
Quick demo script for multi-agent orchestration.
Runs a complete workflow with mock data.
"""

import asyncio
import sys
from pathlib import Path
import json
from datetime import datetime

# Add the apps directory to the path
sys.path.insert(0, str(Path(__file__).parent))

from apps.orchestrator_service.main import orchestrator, settings


async def run_demo():
    """Run a demonstration of the complete workflow."""
    
    print("🚀 Multi-Agent Orchestration Demo")
    print("=" * 50)
    
    # Enable auto-approval for demo
    settings.orchestration.auto_approve_in_dev = True
    
    # Demo parameters
    tenant_id = "demo-tenant"
    brand_id = "acme-corp"
    selected_month = "2024-11"
    prior_year_month = "2023-11"
    
    print(f"Brand: {brand_id}")
    print(f"Target Month: {selected_month}")
    print(f"Comparison: {prior_year_month}")
    print()
    
    try:
        # Start the orchestration
        print("▶️  Starting orchestration workflow...")
        start_time = datetime.now()
        
        result = await orchestrator.run(
            tenant_id=tenant_id,
            brand_id=brand_id,
            selected_month=selected_month,
            prior_year_same_month=prior_year_month,
            metadata={
                "source": "demo_script",
                "demo_version": "1.0.0",
                "timestamp": start_time.isoformat(),
            }
        )
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        # Display results
        print(f"✅ Workflow completed successfully!")
        print(f"   Duration: {duration.total_seconds():.1f} seconds")
        print(f"   Status: {result.status}")
        print(f"   Run ID: {result.run_id}")
        print()
        
        # Show artifacts created
        print("📦 Artifacts Created:")
        for artifact_type, artifact_id in result.artifacts.items():
            print(f"   • {artifact_type}: {artifact_id}")
        print()
        
        # Show approvals
        if result.approvals:
            print("✅ Approvals:")
            for approval in result.approvals:
                print(f"   • {approval.get('artifact_type', 'unknown')}: {approval.get('status', 'unknown')}")
                if approval.get('auto_approved'):
                    print("     (auto-approved in development mode)")
        print()
        
        # Show revision info
        if result.revision_count > 0:
            print(f"🔄 Revisions: {result.revision_count}")
            print()
        
        # Save results
        output_dir = Path(f".artifacts/{brand_id}/{selected_month}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_dir / "demo_results.json"
        with open(output_file, "w") as f:
            json.dump(result.dict(), f, indent=2, default=str)
        
        print(f"💾 Results saved to: {output_file}")
        print()
        
        # Performance summary
        print("📊 Performance Summary:")
        print(f"   • Total Runtime: {duration.total_seconds():.1f}s")
        print(f"   • Phases Completed: {result.current_phase}")
        print(f"   • Final Node: {result.current_node}")
        print(f"   • Error Count: {0 if not result.error else 1}")
        print()
        
        print("🎉 Demo completed successfully!")
        print()
        print("Next steps:")
        print("   1. Review artifacts in .artifacts/ directory")
        print("   2. Run tests: pytest tests/ -v")
        print("   3. Start API server: python -m apps.orchestrator_service.main serve")
        print("   4. View README.md for full documentation")
        
        return result
        
    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        print()
        print("Troubleshooting:")
        print("   1. Check dependencies: pip install -r requirements.txt")
        print("   2. Validate config: python -m apps.orchestrator_service.main validate")
        print("   3. Check logs for detailed error information")
        raise


if __name__ == "__main__":
    # Run the demo
    try:
        result = asyncio.run(run_demo())
        print(f"\n🏁 Demo completed with status: {result.status}")
    except KeyboardInterrupt:
        print("\n🛑 Demo interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Demo failed with error: {e}")
        sys.exit(1)