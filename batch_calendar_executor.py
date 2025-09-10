#!/usr/bin/env python3
"""
Batch Calendar Executor
Runs the calendar planning workflow for all configured clients
"""

import asyncio
import json
import sys
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import logging
from google.cloud import firestore

# Add project paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "emailpilot_graph"))

# Import the calendar workflow
from emailpilot_graph.calendar_workflow import run_calendar_workflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Client configuration
CLIENTS = [
    {
        "id": "rogue-creamery",
        "name": "Rogue Creamery",
        "sales_goal": 75000,
        "optimization": "revenue",
        "campaigns": 8
    },
    {
        "id": "christopher-bean-coffee",
        "name": "Christopher Bean Coffee",
        "sales_goal": 50000,
        "optimization": "balanced",
        "campaigns": 8
    },
    {
        "id": "colorado-hemp-honey",
        "name": "Colorado Hemp Honey",
        "sales_goal": 40000,
        "optimization": "engagement",
        "campaigns": 6
    },
    {
        "id": "milagro-mushrooms",
        "name": "Milagro Mushrooms",
        "sales_goal": 35000,
        "optimization": "balanced",
        "campaigns": 6
    },
    {
        "id": "rocky-mountain-spice",
        "name": "Rocky Mountain Spice Company",
        "sales_goal": 45000,
        "optimization": "revenue",
        "campaigns": 8
    },
    {
        "id": "the-frozen-garden",
        "name": "The Frozen Garden",
        "sales_goal": 60000,
        "optimization": "balanced",
        "campaigns": 8
    },
    {
        "id": "wyoming-wildflower-honey",
        "name": "Wyoming Wildflower Honey",
        "sales_goal": 30000,
        "optimization": "engagement",
        "campaigns": 6
    }
]

class BatchCalendarExecutor:
    """Executes calendar workflow for multiple clients"""
    
    def __init__(self, save_to_firestore: bool = True, llm_type: str = "gemini"):
        """
        Initialize the batch executor
        
        Args:
            save_to_firestore: Whether to save results to Firestore
            llm_type: LLM provider to use ("gemini", "gpt-4", "claude")
        """
        self.save_to_firestore = save_to_firestore
        self.db = firestore.Client() if save_to_firestore else None
        self.results = {}
        self.start_time = None
        self.llm_type = llm_type
        
    async def execute_for_client(
        self,
        client: Dict[str, any],
        month: str
    ) -> Dict[str, any]:
        """
        Execute calendar workflow for a single client
        
        Args:
            client: Client configuration
            month: Target month (YYYY-MM)
            
        Returns:
            Execution result
        """
        logger.info(f"🚀 Starting workflow for {client['name']}")
        
        try:
            # Execute the workflow
            result = await run_calendar_workflow(
                client_id=client["id"],
                client_name=client["name"],
                selected_month=month,
                campaign_count=client["campaigns"],
                sales_goal=client["sales_goal"],
                optimization_goal=client["optimization"],
                llm_type=self.llm_type
            )
            
            # Check if successful
            if result.get("status") == "completed" and result.get("final_calendar"):
                calendar = result["final_calendar"]
                campaigns = calendar.get("campaigns", [])
                
                # Save to Firestore if enabled
                if self.save_to_firestore:
                    await self.save_calendar_to_firestore(client["id"], month, calendar)
                
                # Log success
                logger.info(
                    f"✅ {client['name']}: Generated {len(campaigns)} campaigns | "
                    f"Expected Revenue: ${calendar['summary']['expected_revenue']:,.0f} | "
                    f"Goal Achievement: {calendar['summary']['goal_achievement']:.1f}%"
                )
                
                return {
                    "status": "success",
                    "client_id": client["id"],
                    "client_name": client["name"],
                    "campaigns": len(campaigns),
                    "expected_revenue": calendar["summary"]["expected_revenue"],
                    "goal_achievement": calendar["summary"]["goal_achievement"],
                    "execution_time": result.get("execution_time", 0)
                }
                
            else:
                raise Exception(result.get("error", "Workflow did not complete successfully"))
                
        except Exception as e:
            logger.error(f"❌ {client['name']}: {str(e)}")
            return {
                "status": "error",
                "client_id": client["id"],
                "client_name": client["name"],
                "error": str(e)
            }
    
    async def save_calendar_to_firestore(
        self,
        client_id: str,
        month: str,
        calendar: Dict[str, any]
    ):
        """Save calendar to Firestore"""
        try:
            doc_ref = self.db.collection("calendars").document(f"{client_id}_{month}")
            doc_ref.set({
                "client_id": client_id,
                "month": month,
                "campaigns": calendar.get("campaigns", []),
                "summary": calendar.get("summary", {}),
                "validation": calendar.get("validation", {}),
                "created_at": datetime.now(),
                "created_by": "batch_executor",
                "workflow_version": "2.0"
            })
            logger.debug(f"📁 Saved calendar to Firestore: {client_id}_{month}")
        except Exception as e:
            logger.warning(f"Failed to save to Firestore: {e}")
    
    async def execute_all(
        self,
        month: str = None,
        clients: List[Dict] = None,
        delay_seconds: int = 2
    ) -> Dict[str, any]:
        """
        Execute workflow for all clients
        
        Args:
            month: Target month (YYYY-MM), defaults to next month
            clients: List of clients to process, defaults to all
            delay_seconds: Delay between client executions
            
        Returns:
            Execution summary
        """
        # Default to next month if not specified
        if not month:
            next_month = datetime.now().month + 1
            year = datetime.now().year
            if next_month > 12:
                next_month = 1
                year += 1
            month = f"{year:04d}-{next_month:02d}"
        
        # Use provided clients or default list
        clients_to_process = clients or CLIENTS
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📅 BATCH CALENDAR GENERATION FOR {month}")
        logger.info(f"📊 Processing {len(clients_to_process)} clients")
        logger.info(f"{'='*60}\n")
        
        self.start_time = datetime.now()
        self.results = {}
        
        # Process each client
        for i, client in enumerate(clients_to_process, 1):
            logger.info(f"\n[{i}/{len(clients_to_process)}] Processing {client['name']}...")
            
            # Execute workflow
            result = await self.execute_for_client(client, month)
            self.results[client["id"]] = result
            
            # Delay between clients to avoid overwhelming APIs
            if i < len(clients_to_process):
                await asyncio.sleep(delay_seconds)
        
        # Calculate summary statistics
        total_time = (datetime.now() - self.start_time).total_seconds()
        successful = sum(1 for r in self.results.values() if r["status"] == "success")
        failed = len(self.results) - successful
        
        total_campaigns = sum(
            r.get("campaigns", 0) for r in self.results.values()
            if r["status"] == "success"
        )
        
        total_revenue = sum(
            r.get("expected_revenue", 0) for r in self.results.values()
            if r["status"] == "success"
        )
        
        # Print summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 EXECUTION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"✅ Successful: {successful}/{len(clients_to_process)}")
        if failed > 0:
            logger.info(f"❌ Failed: {failed}")
        logger.info(f"📧 Total Campaigns: {total_campaigns}")
        logger.info(f"💰 Total Expected Revenue: ${total_revenue:,.2f}")
        logger.info(f"⏱️  Total Time: {total_time:.1f}s")
        logger.info(f"⚡ Avg Time per Client: {total_time/len(clients_to_process):.1f}s")
        logger.info(f"{'='*60}\n")
        
        # Save summary to file
        summary = {
            "execution_date": datetime.now().isoformat(),
            "month": month,
            "statistics": {
                "total_clients": len(clients_to_process),
                "successful": successful,
                "failed": failed,
                "total_campaigns": total_campaigns,
                "total_expected_revenue": total_revenue,
                "execution_time": total_time
            },
            "results": self.results
        }
        
        # Save to JSON file
        output_file = f"calendar_batch_{month}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        logger.info(f"💾 Results saved to {output_file}")
        
        return summary
    
    async def execute_single(self, client_id: str, month: str = None) -> Dict[str, any]:
        """
        Execute workflow for a single client by ID
        
        Args:
            client_id: Client identifier
            month: Target month (YYYY-MM)
            
        Returns:
            Execution result
        """
        # Find client configuration
        client = next((c for c in CLIENTS if c["id"] == client_id), None)
        
        if not client:
            raise ValueError(f"Client {client_id} not found")
        
        # Default to next month if not specified
        if not month:
            next_month = datetime.now().month + 1
            year = datetime.now().year
            if next_month > 12:
                next_month = 1
                year += 1
            month = f"{year:04d}-{next_month:02d}"
        
        logger.info(f"Executing workflow for {client['name']} - {month}")
        result = await self.execute_for_client(client, month)
        
        return result

async def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Calendar Executor")
    parser.add_argument(
        "--month",
        help="Target month (YYYY-MM)",
        default=None
    )
    parser.add_argument(
        "--client",
        help="Single client ID to process",
        default=None
    )
    parser.add_argument(
        "--no-firestore",
        action="store_true",
        help="Don't save to Firestore"
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=2,
        help="Delay between clients in seconds"
    )
    
    args = parser.parse_args()
    
    # Create executor
    executor = BatchCalendarExecutor(save_to_firestore=not args.no_firestore)
    
    # Execute based on arguments
    if args.client:
        # Single client execution
        result = await executor.execute_single(args.client, args.month)
        print(json.dumps(result, indent=2, default=str))
    else:
        # Batch execution for all clients
        summary = await executor.execute_all(
            month=args.month,
            delay_seconds=args.delay
        )
        
        # Return exit code based on results
        failed = summary["statistics"]["failed"]
        sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    asyncio.run(main())