#!/usr/bin/env python3

"""
Enhanced Email/SMS Multi-Agent Server with Robust Instruction Tuning
Implements best practices for instruction-based agent behavior
"""

import asyncio
import json
from typing import Any, Dict, List, Optional
import logging
from datetime import datetime
from agent_instructions import (
    InstructionOrchestrator,
    ContentStrategistInstructions,
    CopywriterInstructions,
    DesignerInstructions,
    SegmentationExpertInstructions
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enhanced-email-sms-server")

class EnhancedEmailSMSAgent:
    """Enhanced base class with instruction support"""
    
    def __init__(self, name: str, role: str, expertise: List[str]):
        self.name = name
        self.role = role
        self.expertise = expertise
        self.context = {}
        self.instructions = []
        self.performance_metrics = {}
        
    def set_instructions(self, instructions: List):
        """Set agent-specific instructions"""
        self.instructions = instructions
        
    def update_context(self, context: Dict[str, Any]):
        """Update agent context with shared information"""
        self.context.update(context)
        
    def apply_instructions_to_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Apply relevant instructions to the request processing"""
        # Filter instructions based on request type
        relevant_instructions = []
        
        campaign_type = request.get("campaign_type", "general")
        for instruction in self.instructions:
            if hasattr(instruction, 'category'):
                # Check if instruction is relevant to current campaign type
                if campaign_type in instruction.category or instruction.category in ["role_definition", "output_format"]:
                    relevant_instructions.append(instruction)
        
        return {
            "original_request": request,
            "applied_instructions": len(relevant_instructions),
            "instruction_categories": [inst.category for inst in relevant_instructions if hasattr(inst, 'category')]
        }
    
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process request with instruction enhancement"""
        raise NotImplementedError

class EnhancedContentStrategistAgent(EnhancedEmailSMSAgent):
    """Enhanced Content Strategist with robust instructions"""
    
    def __init__(self):
        super().__init__(
            name="content_strategist",
            role="Campaign Strategy and Messaging Framework",
            expertise=["campaign_strategy", "messaging_framework", "brand_positioning", "customer_journey"]
        )
        self.instruction_set = ContentStrategistInstructions()
        
    async def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        campaign_type = request.get("campaign_type", "general")
        target_audience = request.get("target_audience", "general")
        objectives = request.get("objectives", [])
        
        # Apply instructions
        instruction_context = self.apply_instructions_to_request(request)
        
        # Enhanced strategy based on instructions
        strategy = {
            "campaign_framework": {
                "primary_message": self._generate_enhanced_message(campaign_type, target_audience, objectives),
                "messaging_pillars": self._create_robust_pillars(objectives),
                "customer_journey_stage": self._identify_journey_stage(request),
                "psychological_triggers": self._apply_psychology_principles(target_audience),
                "tone_and_voice": self._define_contextual_tone(target_audience, campaign_type)
            },
            "strategic_recommendations": {
                "timing": self._optimize_send_timing(campaign_type, target_audience),
                "frequency": self._calculate_optimal_frequency(campaign_type),
                "channel_mix": self._optimize_channel_mix(request),
                "segmentation_strategy": self._develop_segmentation(target_audience),
                "success_metrics": self._define_kpis(objectives)
            },
            "instruction_context": instruction_context
        }
        
        return {
            "agent": self.name,
            "strategy": strategy,
            "confidence_score": self._calculate_confidence(strategy),
            "next_steps": ["copywriter", "segmentation_expert"]
        }
    
    def _generate_enhanced_message(self, campaign_type: str, audience: str, objectives: List[str]) -> Dict:
        """Generate primary message with instruction enhancement"""
        
        message_framework = {
            "hook": self._create_hook(campaign_type, audience),
            "value_proposition": self._define_value_prop(objectives),
            "differentiation": self._identify_differentiators(campaign_type),
            "proof_points": self._gather_proof_points(audience)
        }
        
        # Apply campaign-specific enhancements
        if campaign_type == "promotional":
            message_framework["urgency_factor"] = "limited_time"
            message_framework["incentive_structure"] = "tiered_discount"
        elif campaign_type == "welcome_series":
            message_framework["relationship_building"] = "progressive_value"
            message_framework["education_focus"] = "high"
        elif campaign_type == "re_engagement":
            message_framework["acknowledgment"] = "time_sensitive"
            message_framework["win_back_strategy"] = "progressive_incentive"
        
        return message_framework
    
    def _create_hook(self, campaign_type: str, audience: str) -> str:
        hooks = {
            "promotional": f"Exclusive offer for our {audience}",
            "newsletter": f"This week's insights for {audience}",
            "flash_sale": f"⚡ Urgent: Limited availability for {audience}",
            "welcome_series": f"Welcome! Here's what makes us special",
            "re_engagement": f"We've missed you - here's what's new"
        }
        return hooks.get(campaign_type, f"Important update for {audience}")
    
    def _define_value_prop(self, objectives: List[str]) -> str:
        if "increase_sales" in objectives:
            return "Save money on products you love"
        elif "drive_engagement" in objectives:
            return "Stay connected with exclusive content"
        elif "educate" in objectives:
            return "Learn something new every week"
        else:
            return "Get more value from your relationship with us"
    
    def _identify_differentiators(self, campaign_type: str) -> List[str]:
        return ["quality", "service", "value", "expertise", "community"]
    
    def _gather_proof_points(self, audience: str) -> List[str]:
        return ["10,000+ satisfied customers", "4.8★ average rating", "30-day guarantee"]
    
    def _create_robust_pillars(self, objectives: List[str]) -> List[Dict]:
        pillars = []
        for obj in objectives:
            pillars.append({
                "objective": obj,
                "message": f"Achieve {obj.replace('_', ' ')}",
                "support": "Data-driven approach",
                "emotion": "confidence" if "increase" in obj else "excitement"
            })
        return pillars
    
    def _identify_journey_stage(self, request: Dict[str, Any]) -> str:
        customer_data = request.get("customer_data", {})
        if customer_data.get("is_new_customer"):
            return "awareness"
        elif customer_data.get("purchase_count", 0) > 5:
            return "advocacy"
        elif customer_data.get("last_purchase_days", 999) < 30:
            return "retention"
        else:
            return "consideration"
    
    def _apply_psychology_principles(self, audience: str) -> List[str]:
        """Apply behavioral psychology principles"""
        principles = ["reciprocity", "social_proof", "authority"]
        
        if "high_value" in audience.lower():
            principles.append("exclusivity")
        if "new" in audience.lower():
            principles.append("commitment_consistency")
        if "dormant" in audience.lower():
            principles.append("loss_aversion")
            
        return principles
    
    def _define_contextual_tone(self, audience: str, campaign_type: str) -> Dict:
        tone_matrix = {
            "promotional": {"formality": "casual", "energy": "high", "emotion": "exciting"},
            "newsletter": {"formality": "professional", "energy": "moderate", "emotion": "informative"},
            "flash_sale": {"formality": "casual", "energy": "urgent", "emotion": "exciting"},
            "welcome_series": {"formality": "friendly", "energy": "welcoming", "emotion": "warm"},
            "re_engagement": {"formality": "casual", "energy": "moderate", "emotion": "nostalgic"}
        }
        
        base_tone = tone_matrix.get(campaign_type, {"formality": "professional", "energy": "moderate", "emotion": "neutral"})
        
        # Adjust for audience
        if "vip" in audience.lower() or "high_value" in audience.lower():
            base_tone["formality"] = "premium"
        
        return base_tone
    
    def _optimize_send_timing(self, campaign_type: str, audience: str) -> Dict:
        """Optimize send timing based on campaign and audience"""
        timing_recommendations = {
            "day_of_week": "Tuesday-Thursday" if "b2b" in audience.lower() else "Thursday-Saturday",
            "time_of_day": "10am-2pm" if "business" in audience.lower() else "6pm-9pm",
            "timezone": "recipient_local",
            "urgency": "high" if campaign_type == "flash_sale" else "moderate"
        }
        return timing_recommendations
    
    def _calculate_optimal_frequency(self, campaign_type: str) -> str:
        frequency_map = {
            "promotional": "2-3 per week maximum",
            "newsletter": "weekly",
            "flash_sale": "immediate_single_send",
            "welcome_series": "5 emails over 14 days",
            "re_engagement": "3 attempts over 30 days"
        }
        return frequency_map.get(campaign_type, "1-2 per week")
    
    def _optimize_channel_mix(self, request: Dict[str, Any]) -> List[str]:
        channels = ["email"]
        if request.get("include_sms", False):
            channels.append("sms")
        if request.get("urgency", "") == "high":
            channels.append("push_notification")
        return channels
    
    def _develop_segmentation(self, audience: str) -> Dict:
        return {
            "primary_segment": audience,
            "sub_segments": ["engaged", "passive", "at_risk"],
            "exclusions": ["recent_purchasers", "complaint_list"],
            "size_estimate": "10,000-50,000"
        }
    
    def _define_kpis(self, objectives: List[str]) -> List[Dict]:
        kpis = []
        for obj in objectives:
            if "sales" in obj:
                kpis.append({"metric": "revenue", "target": "+20%", "timeframe": "30_days"})
            elif "engagement" in obj:
                kpis.append({"metric": "click_rate", "target": ">5%", "timeframe": "campaign"})
            elif "retention" in obj:
                kpis.append({"metric": "churn_rate", "target": "<2%", "timeframe": "90_days"})
        return kpis
    
    def _calculate_confidence(self, strategy: Dict) -> float:
        """Calculate confidence score based on strategy completeness"""
        score = 0.5  # Base score
        
        if strategy.get("campaign_framework", {}).get("psychological_triggers"):
            score += 0.1
        if strategy.get("strategic_recommendations", {}).get("success_metrics"):
            score += 0.1
        if len(strategy.get("campaign_framework", {}).get("messaging_pillars", [])) > 2:
            score += 0.1
        if strategy.get("strategic_recommendations", {}).get("segmentation_strategy"):
            score += 0.1
        if strategy.get("instruction_context", {}).get("applied_instructions", 0) > 3:
            score += 0.1
            
        return min(score, 1.0)

class EnhancedMultiAgentOrchestrator:
    """Enhanced orchestrator with instruction management"""
    
    def __init__(self):
        self.agents = {
            "content_strategist": EnhancedContentStrategistAgent()
        }
        # Add more enhanced agents as needed
        
        self.instruction_orchestrator = InstructionOrchestrator()
        self.workflow_context = {}
        self.performance_history = []
        
    async def orchestrate_campaign_creation(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate campaign creation with enhanced instruction support"""
        
        start_time = datetime.now()
        workflow_results = {}
        
        # Get relevant instructions for this campaign
        campaign_type = request.get("campaign_type", "general")
        instructions = self.instruction_orchestrator.get_instructions_for_campaign(
            campaign_type=campaign_type,
            context=request
        )
        
        # Apply instructions to each agent
        for agent_name, agent_instructions in instructions.items():
            if agent_name in self.agents:
                self.agents[agent_name].set_instructions(agent_instructions)
        
        # Execute workflow with enhanced agents
        logger.info(f"Starting enhanced campaign creation for {campaign_type}")
        
        # Step 1: Enhanced Strategy Development
        if "content_strategist" in self.agents:
            strategy_result = await self.agents["content_strategist"].process_request(request)
            workflow_results["strategy"] = strategy_result
            self.workflow_context.update(strategy_result)
        
        # Add more workflow steps as agents are enhanced
        
        # Calculate execution metrics
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Generate final output
        final_output = {
            "campaign_creation_complete": True,
            "workflow_results": workflow_results,
            "applied_instructions": {
                agent: len(insts) for agent, insts in instructions.items()
            },
            "execution_metrics": {
                "time_seconds": execution_time,
                "agents_used": len(workflow_results),
                "confidence_score": self._calculate_overall_confidence(workflow_results)
            },
            "final_recommendations": self._generate_enhanced_recommendations(workflow_results, campaign_type)
        }
        
        # Store for learning
        self.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            "campaign_type": campaign_type,
            "metrics": final_output["execution_metrics"]
        })
        
        return final_output
    
    def _calculate_overall_confidence(self, workflow_results: Dict) -> float:
        """Calculate overall workflow confidence"""
        confidences = []
        for result in workflow_results.values():
            if isinstance(result, dict) and "confidence_score" in result:
                confidences.append(result["confidence_score"])
        
        return sum(confidences) / len(confidences) if confidences else 0.5
    
    def _generate_enhanced_recommendations(self, workflow_results: Dict, campaign_type: str) -> List[str]:
        """Generate enhanced recommendations based on results"""
        recommendations = [
            f"Campaign type '{campaign_type}' configured with best practices",
            "All agents applied domain-specific instructions",
            "Review confidence scores for each component"
        ]
        
        # Add specific recommendations based on results
        if "strategy" in workflow_results:
            strategy = workflow_results["strategy"].get("strategy", {})
            if strategy.get("strategic_recommendations", {}).get("success_metrics"):
                recommendations.append("KPIs defined - set up tracking before launch")
            
            psych_triggers = strategy.get("campaign_framework", {}).get("psychological_triggers", [])
            if psych_triggers:
                recommendations.append(f"Leverage {', '.join(psych_triggers[:2])} in creative")
        
        return recommendations

# Example usage
async def test_enhanced_system():
    """Test the enhanced multi-agent system"""
    
    orchestrator = EnhancedMultiAgentOrchestrator()
    
    # Test with a promotional campaign
    test_request = {
        "campaign_type": "promotional",
        "target_audience": "high-value customers who haven't purchased in 30 days",
        "objectives": ["increase_sales", "drive_engagement", "reduce_churn"],
        "brand_guidelines": {
            "tone": "premium",
            "colors": {"primary": "#000000", "accent": "#gold"}
        },
        "customer_data": {
            "segments": ["vip", "dormant"],
            "average_order_value": 250,
            "purchase_frequency": "quarterly"
        }
    }
    
    result = await orchestrator.orchestrate_campaign_creation(test_request)
    
    print("Enhanced Campaign Creation Result:")
    print(json.dumps(result, indent=2, default=str))
    
    return result

if __name__ == "__main__":
    asyncio.run(test_enhanced_system())