#!/usr/bin/env python3
"""
Migration Script: Unify AI Agent Management

This script migrates agent definitions from multiple sources into the unified agents collection:
1. Prompts from ai_prompts collection (category="agent") 
2. Hardcoded agents from copywriting tool
3. Any existing agent definitions from admin dashboard

Run this once to establish the Single Source of Truth.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from google.cloud import firestore
from typing import List, Dict, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_firestore():
    """Initialize Firestore client"""
    try:
        # Set project ID from environment or use default
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "emailpilot-438321")
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        
        db = firestore.Client(project=project_id)
        logger.info(f"✅ Connected to Firestore project: {project_id}")
        return db
    except Exception as e:
        logger.error(f"❌ Failed to initialize Firestore: {e}")
        return None

def migrate_prompts_to_agents(db: firestore.Client) -> int:
    """Migrate agent-category prompts to unified agents collection"""
    logger.info("📋 Migrating agent prompts from ai_prompts collection...")
    
    try:
        # Get all prompts with category="agent"
        prompts_ref = db.collection("ai_prompts").where("category", "==", "agent")
        agent_prompts = list(prompts_ref.stream())
        
        migrated_count = 0
        for doc in agent_prompts:
            prompt_data = doc.to_dict()
            
            # Extract agent info from prompt
            agent_type = prompt_data.get("metadata", {}).get("agent_type", "general")
            agent_id = agent_type.lower().replace(" ", "_").replace("-", "_")
            
            # Check if agent already exists in unified collection
            if db.collection("agents").document(agent_id).get().exists:
                logger.info(f"⏭️  Agent '{agent_id}' already exists in unified collection")
                continue
                
            # Create unified agent from prompt data
            agent_data = {
                "agent_id": agent_id,
                "display_name": prompt_data.get("name", agent_type.title()),
                "role": agent_type,
                "default_provider": prompt_data.get("model_provider", "auto"),
                "default_model_id": prompt_data.get("model_name"),
                "prompt_template": prompt_data.get("prompt_template", ""),
                "capabilities": prompt_data.get("variables", []),
                "active": prompt_data.get("active", True),
                "description": prompt_data.get("description", ""),
                "version": prompt_data.get("version", 1),
                "variables": prompt_data.get("variables", []),
                "created_at": prompt_data.get("created_at", datetime.utcnow()),
                "updated_at": datetime.utcnow(),
                "metadata": {
                    "migrated_from": "ai_prompts",
                    "original_prompt_id": doc.id,
                    "migration_date": datetime.utcnow().isoformat(),
                    "source_file": prompt_data.get("metadata", {}).get("source_file", "unknown")
                }
            }
            
            # Save to unified agents collection
            db.collection("agents").document(agent_id).set(agent_data)
            migrated_count += 1
            logger.info(f"✅ Migrated agent: {agent_id} ({agent_data['display_name']})")
        
        logger.info(f"📋 Migrated {migrated_count} agent prompts")
        return migrated_count
        
    except Exception as e:
        logger.error(f"❌ Failed to migrate prompts: {e}")
        return 0

def seed_copywriting_agents(db: firestore.Client) -> int:
    """Seed agents used by the copywriting tool"""
    logger.info("✍️ Seeding copywriting tool agents...")
    
    copywriting_agents = [
        {
            "agent_id": "copywriter",
            "display_name": "Expert Copywriter", 
            "role": "copywriter",
            "default_provider": "claude",
            "default_model_id": "claude-3-5-sonnet-20241022",
            "prompt_template": """You are an expert email copywriter with 10+ years of experience in direct-response marketing. Your specialty is creating compelling email campaigns that drive engagement and conversions.

Your key strengths:
- Writing attention-grabbing subject lines that increase open rates
- Crafting persuasive email body copy using proven frameworks (AIDA, PAS, FOMO, etc.)
- Creating strong calls-to-action that drive clicks and conversions
- Adapting tone and style to match brand voice and target audience
- A/B testing recommendations for optimization

Always consider:
- Brand voice and personality
- Target audience demographics and psychographics
- Campaign goals and KPIs
- Email deliverability best practices
- Mobile optimization""",
            "capabilities": ["email_copy", "subject_lines", "cta_creation", "brand_voice", "ab_testing"],
            "description": "Expert in email copy and messaging, specializing in direct-response marketing",
            "variables": ["brand_voice", "target_audience", "campaign_goal", "product_details"],
            "metadata": {"source": "copywriting_tool", "category": "marketing"}
        },
        {
            "agent_id": "content_strategist",
            "display_name": "Content Strategist",
            "role": "strategist", 
            "default_provider": "gemini",
            "default_model_id": "gemini-1.5-pro-latest",
            "prompt_template": """You are a senior content strategist with expertise in developing comprehensive email marketing strategies. You focus on the big picture - customer journey mapping, content planning, and campaign orchestration.

Your core responsibilities:
- Analyzing customer data and behavior patterns
- Creating content calendars and campaign sequences
- Developing audience segmentation strategies
- Planning customer journey touchpoints
- Coordinating cross-channel marketing efforts

Your approach:
- Data-driven decision making
- Customer-centric content planning
- Brand consistency across all touchpoints
- Performance optimization through testing
- ROI-focused strategy development""",
            "capabilities": ["strategy", "audience_targeting", "campaign_planning", "data_analysis"],
            "description": "Strategic planning and campaign orchestration expert",
            "variables": ["customer_data", "business_goals", "campaign_timeline"],
            "metadata": {"source": "copywriting_tool", "category": "strategy"}
        },
        {
            "agent_id": "designer",
            "display_name": "Email Designer",
            "role": "design",
            "default_provider": "openai", 
            "default_model_id": "gpt-4o",
            "prompt_template": """You are an email design specialist focused on creating visually compelling and conversion-optimized email layouts. You understand both aesthetic principles and email technical constraints.

Your design expertise:
- Email template design and layout optimization
- Visual hierarchy and user experience
- Brand-consistent visual elements
- Mobile-responsive design principles
- Email client compatibility considerations""",
            "capabilities": ["visual_design", "layout_optimization", "mobile_responsive"],
            "description": "Visual design and creative direction specialist",
            "variables": ["brand_colors", "visual_style", "layout_preferences"],
            "metadata": {"source": "copywriting_tool", "category": "design"}
        },
        {
            "agent_id": "brand_specialist",
            "display_name": "Brand Specialist",
            "role": "branding",
            "default_provider": "claude",
            "default_model_id": "claude-3-5-sonnet-20241022", 
            "prompt_template": """You are a brand specialist focused on maintaining consistent brand voice, tone, and messaging across all email communications. You ensure every piece of content aligns with brand guidelines and values.

Your expertise includes:
- Brand voice development and maintenance
- Tone consistency across campaigns
- Brand personality expression in copy
- Visual brand alignment recommendations
- Brand guideline enforcement""",
            "capabilities": ["brand_voice", "tone_consistency", "messaging_alignment"],
            "description": "Ensures brand voice and consistency across all communications",
            "variables": ["brand_guidelines", "brand_values", "brand_personality"],
            "metadata": {"source": "copywriting_tool", "category": "branding"}
        },
        {
            "agent_id": "performance_analyst",
            "display_name": "Performance Analyst",
            "role": "analytics",
            "default_provider": "gemini",
            "default_model_id": "gemini-1.5-flash",
            "prompt_template": """You are a performance analyst specializing in email marketing metrics and optimization. You analyze campaign performance, identify trends, and provide actionable recommendations for improvement.

Your analytical focus:
- Email performance metrics (open rates, click rates, conversions)
- A/B test design and results interpretation
- Audience behavior analysis
- Campaign optimization recommendations
- ROI and revenue attribution""",
            "capabilities": ["metrics_analysis", "performance_optimization", "ab_testing"],
            "description": "Analytics and optimization expert for email campaigns",
            "variables": ["performance_data", "test_results", "kpi_targets"],
            "metadata": {"source": "copywriting_tool", "category": "analytics"}
        }
    ]
    
    seeded_count = 0
    for agent_data in copywriting_agents:
        agent_id = agent_data["agent_id"]
        
        # Check if agent already exists
        if db.collection("agents").document(agent_id).get().exists:
            logger.info(f"⏭️  Agent '{agent_id}' already exists")
            continue
            
        # Add timestamps and make active
        agent_data.update({
            "active": True,
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        
        # Save to Firestore
        db.collection("agents").document(agent_id).set(agent_data)
        seeded_count += 1
        logger.info(f"✅ Seeded agent: {agent_id} ({agent_data['display_name']})")
    
    logger.info(f"✍️ Seeded {seeded_count} copywriting agents")
    return seeded_count

def create_migration_log(db: firestore.Client, results: Dict[str, Any]):
    """Create a migration log entry"""
    log_data = {
        "migration_type": "agents_unification",
        "timestamp": datetime.utcnow(),
        "results": results,
        "version": "1.0.0",
        "status": "completed"
    }
    
    db.collection("migration_logs").add(log_data)
    logger.info("📝 Migration log created")

def main():
    """Main migration function"""
    logger.info("🚀 Starting AI Agent Unification Migration")
    
    # Initialize Firestore
    db = initialize_firestore()
    if not db:
        logger.error("❌ Cannot proceed without Firestore connection")
        sys.exit(1)
    
    # Run migrations
    results = {}
    
    # 1. Migrate agent prompts from ai_prompts collection
    results["prompts_migrated"] = migrate_prompts_to_agents(db)
    
    # 2. Seed copywriting tool agents 
    results["copywriting_agents_seeded"] = seed_copywriting_agents(db)
    
    # 3. Check final state
    agents_count = len(list(db.collection("agents").stream()))
    results["total_unified_agents"] = agents_count
    
    # 4. Create migration log
    create_migration_log(db, results)
    
    # Summary
    logger.info("=" * 50)
    logger.info("🎉 AI Agent Unification Migration Complete!")
    logger.info(f"📊 Results:")
    logger.info(f"   • Prompts migrated: {results['prompts_migrated']}")
    logger.info(f"   • Copywriting agents seeded: {results['copywriting_agents_seeded']}")
    logger.info(f"   • Total unified agents: {results['total_unified_agents']}")
    logger.info("=" * 50)
    logger.info("✅ Next steps:")
    logger.info("   1. Update copywriting tool to use /api/agents endpoint")
    logger.info("   2. Update admin UI to manage unified agents collection")
    logger.info("   3. Deprecate old prompts and agent management systems")
    
if __name__ == "__main__":
    main()