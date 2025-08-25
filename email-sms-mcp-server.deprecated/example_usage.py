#!/usr/bin/env python3

"""
Example usage of the Email/SMS Multi-Agent MCP Server

This file demonstrates how to use the multi-agent system for creating
email and SMS campaigns with specialized AI agents.
"""

import json
import asyncio
from server import MultiAgentOrchestrator

async def example_email_campaign():
    """Example: Create a promotional email campaign"""
    
    print("🚀 Creating Promotional Email Campaign")
    print("=" * 50)
    
    orchestrator = MultiAgentOrchestrator()
    
    # Define campaign requirements
    email_request = {
        "campaign_type": "promotional",
        "target_audience": "high-value customers who haven't purchased in 30 days",
        "objectives": [
            "re-engage_dormant_customers",
            "drive_immediate_sales",
            "showcase_new_products"
        ],
        "brand_guidelines": {
            "tone": "friendly_but_professional",
            "colors": {
                "primary": "#007bff",
                "secondary": "#28a745", 
                "accent": "#ffc107"
            },
            "fonts": {
                "heading": "Montserrat",
                "body": "Open Sans"
            }
        },
        "customer_data": {
            "available_fields": ["first_name", "last_purchase_date", "favorite_category", "location"],
            "segments": ["vip_customers", "dormant_high_value", "category_affinity"],
            "engagement_history": {
                "avg_open_rate": 0.25,
                "avg_click_rate": 0.04,
                "best_send_time": "10:00 AM"
            }
        },
        "content_type": "email"
    }
    
    # Create campaign using multi-agent orchestration
    result = await orchestrator.orchestrate_campaign_creation(email_request)
    
    print("📧 EMAIL CAMPAIGN RESULTS:")
    print("-" * 30)
    print(json.dumps(result, indent=2))
    
    return result

async def example_sms_campaign():
    """Example: Create a flash sale SMS campaign"""
    
    print("\n📱 Creating Flash Sale SMS Campaign")  
    print("=" * 50)
    
    orchestrator = MultiAgentOrchestrator()
    
    # Define SMS campaign requirements
    sms_request = {
        "campaign_type": "flash_sale",
        "target_audience": "mobile-engaged customers with purchase history",
        "objectives": [
            "create_urgency",
            "drive_immediate_action",
            "clear_inventory"
        ],
        "character_limit": 160,
        "customer_data": {
            "available_fields": ["first_name", "last_purchase"],
            "segments": ["mobile_active", "repeat_purchasers"],
            "sms_engagement": {
                "opt_in_rate": 0.15,
                "response_rate": 0.08,
                "best_send_time": "2:00 PM"
            }
        },
        "content_type": "sms",
        "urgency_factors": {
            "time_limit": "24_hours",
            "inventory_status": "limited",
            "discount_percentage": 40
        }
    }
    
    # Create SMS campaign
    result = await orchestrator.orchestrate_campaign_creation(sms_request)
    
    print("📱 SMS CAMPAIGN RESULTS:")
    print("-" * 30)
    print(json.dumps(result, indent=2))
    
    return result

async def example_agent_consultation():
    """Example: Consult individual agents for specific expertise"""
    
    print("\n🤝 Individual Agent Consultations")
    print("=" * 50)
    
    orchestrator = MultiAgentOrchestrator()
    
    # Consult copywriter for subject line optimization
    copywriter_request = {
        "content_type": "email",
        "campaign_context": {
            "type": "welcome_series",
            "audience": "new_subscribers",
            "goal": "high_engagement"
        },
        "requirements": [
            "personalized",
            "curiosity_driven", 
            "mobile_optimized"
        ],
        "constraints": {
            "character_limit": 50,
            "avoid_words": ["free", "urgent", "limited"]
        }
    }
    
    copywriter_result = await orchestrator.agents["copywriter"].process_request(copywriter_request)
    
    print("✍️  COPYWRITER CONSULTATION:")
    print("-" * 30)
    print(json.dumps(copywriter_result, indent=2))
    
    # Consult segmentation expert for audience targeting
    segmentation_request = {
        "campaign_objective": "product_launch",
        "product_category": "premium_skincare",
        "customer_data": {
            "total_subscribers": 50000,
            "purchase_history": True,
            "demographic_data": True,
            "engagement_scores": True
        },
        "targeting_goals": [
            "maximize_relevance",
            "predict_high_intent",
            "optimize_timing"
        ]
    }
    
    segmentation_result = await orchestrator.agents["segmentation_expert"].process_request(segmentation_request)
    
    print("\n🎯 SEGMENTATION EXPERT CONSULTATION:")
    print("-" * 30) 
    print(json.dumps(segmentation_result, indent=2))

async def example_workflow_customization():
    """Example: Demonstrate workflow customization capabilities"""
    
    print("\n⚙️  Custom Workflow Example")
    print("=" * 50)
    
    orchestrator = MultiAgentOrchestrator()
    
    # Custom workflow for newsletter campaign
    newsletter_request = {
        "campaign_type": "newsletter",
        "content_theme": "monthly_industry_insights",
        "target_audience": "engaged_subscribers",
        "content_sections": [
            "industry_news",
            "expert_interview", 
            "product_updates",
            "community_spotlight"
        ],
        "design_requirements": {
            "template_style": "clean_minimal",
            "mobile_first": True,
            "accessibility_compliant": True
        }
    }
    
    # Demonstrate custom agent sequence
    print("🔄 Custom Agent Workflow:")
    
    # Step 1: Strategy
    strategy_result = await orchestrator.agents["content_strategist"].process_request(newsletter_request)
    print("1. ✅ Strategy developed")
    
    # Step 2: Copy (with strategy context)
    copy_request = {**newsletter_request, **strategy_result}
    copy_result = await orchestrator.agents["copywriter"].process_request(copy_request)
    print("2. ✅ Copy created")
    
    # Step 3: Design (with copy context)
    design_request = {**copy_request, **copy_result}
    design_result = await orchestrator.agents["designer"].process_request(design_request)
    print("3. ✅ Design specifications completed")
    
    # Final results
    custom_workflow_result = {
        "workflow_type": "newsletter_creation",
        "strategy": strategy_result,
        "copy": copy_result,
        "design": design_result
    }
    
    print("\n📰 NEWSLETTER WORKFLOW RESULTS:")
    print("-" * 30)
    print(json.dumps(custom_workflow_result, indent=2))

async def main():
    """Run all examples"""
    
    print("🎯 Email/SMS Multi-Agent MCP Server Examples")
    print("=" * 60)
    
    # Run examples
    await example_email_campaign()
    await example_sms_campaign()
    await example_agent_consultation()
    await example_workflow_customization()
    
    print("\n" + "=" * 60)
    print("✨ All examples completed successfully!")
    print("\nTo use in Claude Code:")
    print("1. Install the MCP server: claude mcp add email-sms-agents --transport stdio -- python server.py")
    print("2. Use tools: create_email_campaign, create_sms_campaign, consult_agent")
    print("3. Access agents: content_strategist, copywriter, designer, segmentation_expert")

if __name__ == "__main__":
    asyncio.run(main())