"""
Robust Instruction Sets for Email/SMS Multi-Agent System
Best practices for agent instruction tuning
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class InstructionLevel(Enum):
    """Instruction specificity levels"""
    SYSTEM = "system"  # Core behavior instructions
    DOMAIN = "domain"  # Email/SMS marketing domain knowledge
    TASK = "task"  # Specific task instructions
    CONTEXT = "context"  # Contextual adaptations

@dataclass
class AgentInstruction:
    """Structured instruction format"""
    level: InstructionLevel
    category: str
    instruction: str
    examples: List[str] = None
    constraints: List[str] = None
    quality_metrics: List[str] = None

class ContentStrategistInstructions:
    """Comprehensive instructions for Content Strategist Agent"""
    
    SYSTEM_INSTRUCTIONS = [
        AgentInstruction(
            level=InstructionLevel.SYSTEM,
            category="role_definition",
            instruction="""You are a senior email marketing strategist with 10+ years of experience 
            in developing data-driven campaign strategies. Your role is to create comprehensive 
            messaging frameworks that align with business objectives and customer psychology.""",
            constraints=[
                "Always consider the full customer journey",
                "Base strategies on data and best practices",
                "Maintain brand consistency across all touchpoints"
            ]
        ),
        AgentInstruction(
            level=InstructionLevel.SYSTEM,
            category="output_format",
            instruction="""Structure all strategic outputs using the MECE principle 
            (Mutually Exclusive, Collectively Exhaustive). Provide clear, actionable 
            recommendations with supporting rationale.""",
            quality_metrics=[
                "Clarity of strategic direction",
                "Alignment with objectives",
                "Actionability of recommendations"
            ]
        )
    ]
    
    DOMAIN_INSTRUCTIONS = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="customer_psychology",
            instruction="""Apply behavioral psychology principles including:
            - Reciprocity: Offer value before asking for action
            - Social Proof: Leverage testimonials and user counts
            - Scarcity: Create genuine urgency when appropriate
            - Authority: Establish credibility through expertise
            - Consistency: Align with previous customer interactions
            - Liking: Build affinity through personalization""",
            examples=[
                "Flash Sale: Combine scarcity (24-hour limit) with social proof (500+ customers bought)",
                "Welcome Series: Use reciprocity by offering exclusive content before promotional asks"
            ]
        ),
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="segmentation_strategy",
            instruction="""Develop segmentation strategies based on:
            1. Behavioral data: Purchase history, engagement patterns, browse behavior
            2. Demographic data: Age, location, income (if available)
            3. Psychographic data: Interests, values, lifestyle
            4. Lifecycle stage: New, active, at-risk, churned
            5. Value tier: High-value, mid-value, low-value""",
            constraints=[
                "Ensure segments are measurable and actionable",
                "Avoid over-segmentation (min 1000 contacts per segment)",
                "Consider segment overlap and exclusion rules"
            ]
        ),
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="campaign_timing",
            instruction="""Optimize send timing based on:
            - Industry benchmarks (B2B: Tue-Thu 10am-2pm, B2C: evenings/weekends)
            - Historical engagement data from Klaviyo
            - Time zone considerations
            - Competitive send patterns
            - Customer routine analysis""",
            quality_metrics=[
                "Open rate improvement vs baseline",
                "Click-through rate optimization",
                "Conversion timing analysis"
            ]
        )
    ]
    
    TASK_INSTRUCTIONS = {
        "promotional_campaign": AgentInstruction(
            level=InstructionLevel.TASK,
            category="promotional",
            instruction="""For promotional campaigns:
            1. Lead with value proposition, not discount
            2. Create urgency through limited-time or limited-quantity
            3. Use tiered offers for different segments
            4. Include social proof and testimonials
            5. Clear, prominent CTAs above the fold""",
            examples=[
                "Subject: 'Your exclusive access ends tonight' vs 'Sale ends soon'",
                "Hero: Product benefits first, then '30% off for 24 hours'",
                "CTA: 'Claim Your Discount' vs generic 'Shop Now'"
            ]
        ),
        "welcome_series": AgentInstruction(
            level=InstructionLevel.TASK,
            category="welcome",
            instruction="""Design welcome series with:
            Email 1 (Immediate): Thank you + brand story + single CTA
            Email 2 (Day 2): Educational content + soft product introduction
            Email 3 (Day 5): Social proof + bestsellers
            Email 4 (Day 7): Limited-time welcome offer
            Email 5 (Day 14): Engagement check + preference center""",
            constraints=[
                "No hard sell in first 2 emails",
                "Gradually increase commercial content",
                "Monitor engagement and adjust timing"
            ]
        ),
        "re_engagement": AgentInstruction(
            level=InstructionLevel.TASK,
            category="winback",
            instruction="""Re-engagement strategy:
            1. Acknowledge the time gap naturally
            2. Show what's new since last interaction
            3. Offer exclusive 'we miss you' incentive
            4. Use progressive discounting (10%, 15%, 20%)
            5. Final attempt: Ask for feedback or preference update""",
            quality_metrics=[
                "Reactivation rate > 10%",
                "Unsubscribe rate < 5%",
                "Revenue per reactivated customer"
            ]
        )
    }

class CopywriterInstructions:
    """Comprehensive instructions for Copywriter Agent"""
    
    SYSTEM_INSTRUCTIONS = [
        AgentInstruction(
            level=InstructionLevel.SYSTEM,
            category="writing_style",
            instruction="""Write in active voice with clarity and brevity. Every word must 
            earn its place. Use the inverted pyramid structure: most important information 
            first. Maintain consistent brand voice while adapting tone to context.""",
            constraints=[
                "Subject lines: 30-50 characters optimal",
                "Preview text: 35-90 characters",
                "Mobile-first: Key message in first 3 lines",
                "Sentences: Max 20 words for clarity"
            ]
        )
    ]
    
    SUBJECT_LINE_FORMULAS = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="subject_lines",
            instruction="""Apply proven subject line formulas:
            1. Curiosity Gap: 'The one thing you're missing in [topic]'
            2. Benefit-Driven: 'How to [achieve desired outcome] in [timeframe]'
            3. Urgency: '[Time] left to [benefit]'
            4. Personalization: '[Name], your [item] is ready'
            5. Question: 'Ready to [achieve goal]?'
            6. Number/List: '5 ways to [solve problem]'
            7. Exclusivity: 'Exclusive: [benefit] for our best customers'""",
            examples=[
                "Curiosity: 'The secret ingredient top performers use'",
                "Benefit: 'Double your email opens in 7 days'",
                "Urgency: '12 hours left: Your cart expires'",
                "Personal: 'Sarah, your style profile is ready'",
                "Question: 'Still thinking about those shoes?'",
                "Number: '3 mistakes killing your conversions'",
                "Exclusive: 'VIP early access starts now'"
            ],
            quality_metrics=[
                "Open rate > 25% for promotional",
                "Open rate > 35% for transactional",
                "Low spam complaints < 0.1%"
            ]
        )
    ]
    
    CTA_OPTIMIZATION = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="cta_buttons",
            instruction="""CTA button copy rules:
            1. Use action verbs: Get, Start, Discover, Claim, Reserve
            2. Create urgency: Now, Today, Before it's gone
            3. Personalize: My discount, Your reward
            4. Be specific: 'Get 30% Off' vs 'Shop Sale'
            5. Test button vs text links for different segments""",
            examples=[
                "E-commerce: 'Add to Cart' → 'Reserve Yours'",
                "SaaS: 'Sign Up' → 'Start Free Trial'",
                "Content: 'Read More' → 'Get the Guide'",
                "Event: 'Register' → 'Save My Seat'"
            ],
            constraints=[
                "Mobile buttons: 44x44px minimum tap target",
                "Contrast ratio: 4.5:1 minimum",
                "Above the fold placement",
                "Repeat CTA every 2-3 scroll depths"
            ]
        )
    ]
    
    SMS_SPECIFIC = [
        AgentInstruction(
            level=InstructionLevel.TASK,
            category="sms_copy",
            instruction="""SMS copywriting rules:
            1. Front-load the value/offer
            2. Use SMS shorthand sparingly
            3. Include clear opt-out: 'Reply STOP to unsubscribe'
            4. One clear CTA per message
            5. Use URL shorteners with tracking""",
            examples=[
                "Flash sale: 'FLASH SALE! 40% off everything. Today only: [link] Reply STOP to opt out'",
                "Cart abandon: 'Hi [Name]! Your cart expires in 2 hrs. Complete order: [link] STOP to unsub'",
                "VIP: 'VIP EXCLUSIVE: Early access starts now. Shop before everyone else: [link] STOP to end'"
            ],
            constraints=[
                "160 characters for single SMS",
                "Include brand name in first 20 chars",
                "Compliance: Include opt-out",
                "No excessive capitalization (max 30%)"
            ]
        )
    ]

class DesignerInstructions:
    """Comprehensive instructions for Designer Agent"""
    
    VISUAL_HIERARCHY = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="layout_principles",
            instruction="""Apply visual hierarchy principles:
            1. Size: Larger elements draw attention first
            2. Color: High contrast for primary CTAs
            3. Spacing: White space to reduce cognitive load
            4. Alignment: Consistent grid system (8px base)
            5. Repetition: Consistent patterns for scannability
            6. Proximity: Group related elements""",
            quality_metrics=[
                "F-pattern or Z-pattern scan optimization",
                "3-second glance test success",
                "Mobile responsiveness score > 95%"
            ]
        )
    ]
    
    EMAIL_TEMPLATE_SPECS = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="technical_specs",
            instruction="""Email template technical requirements:
            - Width: 600px maximum for desktop
            - Mobile: Single column below 480px
            - Images: Optimize for 2x retina displays
            - Alt text: Descriptive for all images
            - Fonts: Web-safe with fallbacks
            - Load time: < 3 seconds on 3G""",
            constraints=[
                "HTML tables for layout (not divs)",
                "Inline CSS for maximum compatibility",
                "Total email size < 100KB",
                "Image-to-text ratio 40:60 maximum"
            ]
        )
    ]

class SegmentationExpertInstructions:
    """Comprehensive instructions for Segmentation Expert Agent"""
    
    SEGMENTATION_FRAMEWORK = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="rfm_analysis",
            instruction="""Implement RFM (Recency, Frequency, Monetary) segmentation:
            Recency: Last purchase/engagement date
            - Hot: 0-30 days (score: 5)
            - Warm: 31-90 days (score: 3-4)
            - Cold: 91-180 days (score: 2)
            - Frozen: 180+ days (score: 1)
            
            Frequency: Purchase/engagement count
            - Very High: 10+ (score: 5)
            - High: 5-9 (score: 4)
            - Medium: 2-4 (score: 3)
            - Low: 1 (score: 2)
            - None: 0 (score: 1)
            
            Monetary: Total lifetime value
            - Top: >$1000 (score: 5)
            - High: $500-999 (score: 4)
            - Medium: $100-499 (score: 3)
            - Low: $50-99 (score: 2)
            - Minimal: <$50 (score: 1)""",
            examples=[
                "Champions (555, 554, 545): Best customers, reward them",
                "Loyal (535-543): Upsell higher value products",
                "At Risk (331-343): Re-engage with special offers",
                "Lost (111-222): Require win-back campaign"
            ]
        )
    ]
    
    PREDICTIVE_SEGMENTATION = [
        AgentInstruction(
            level=InstructionLevel.DOMAIN,
            category="predictive_models",
            instruction="""Apply predictive segmentation:
            1. Churn Prediction: Identify at-risk customers
               - Decreasing engagement frequency
               - Reduced average order value
               - Increased time between purchases
               
            2. CLV Prediction: Future value estimation
               - Purchase frequency trend
               - Average order value trend
               - Category expansion behavior
               
            3. Next Best Action: Personalized recommendations
               - Browse behavior patterns
               - Purchase sequence analysis
               - Seasonal preferences""",
            quality_metrics=[
                "Segment precision > 70%",
                "Segment recall > 60%",
                "Lift in conversion > 20% vs control"
            ]
        )
    ]

class InstructionOrchestrator:
    """Orchestrates instructions across all agents"""
    
    def __init__(self):
        self.agents_instructions = {
            "content_strategist": ContentStrategistInstructions(),
            "copywriter": CopywriterInstructions(),
            "designer": DesignerInstructions(),
            "segmentation_expert": SegmentationExpertInstructions()
        }
        
    def get_instructions_for_campaign(self, 
                                     campaign_type: str, 
                                     context: Dict[str, Any]) -> Dict[str, List[AgentInstruction]]:
        """Get relevant instructions for a specific campaign type and context"""
        
        instructions = {}
        
        # Base instructions for all agents
        for agent_name, agent_instructions in self.agents_instructions.items():
            agent_inst_list = []
            
            # Add system-level instructions
            if hasattr(agent_instructions, 'SYSTEM_INSTRUCTIONS'):
                agent_inst_list.extend(agent_instructions.SYSTEM_INSTRUCTIONS)
            
            # Add domain-specific instructions
            if hasattr(agent_instructions, 'DOMAIN_INSTRUCTIONS'):
                agent_inst_list.extend(agent_instructions.DOMAIN_INSTRUCTIONS)
            
            # Add task-specific instructions based on campaign type
            if hasattr(agent_instructions, 'TASK_INSTRUCTIONS'):
                if campaign_type in agent_instructions.TASK_INSTRUCTIONS:
                    agent_inst_list.append(
                        agent_instructions.TASK_INSTRUCTIONS[campaign_type]
                    )
            
            instructions[agent_name] = agent_inst_list
        
        return instructions
    
    def format_instructions_for_prompt(self, 
                                      instructions: List[AgentInstruction]) -> str:
        """Format instructions for inclusion in agent prompts"""
        
        prompt_sections = []
        
        # Group by level
        by_level = {}
        for inst in instructions:
            if inst.level not in by_level:
                by_level[inst.level] = []
            by_level[inst.level].append(inst)
        
        # Format each level
        for level in [InstructionLevel.SYSTEM, InstructionLevel.DOMAIN, 
                     InstructionLevel.TASK, InstructionLevel.CONTEXT]:
            if level in by_level:
                prompt_sections.append(f"\n## {level.value.upper()} INSTRUCTIONS\n")
                
                for inst in by_level[level]:
                    prompt_sections.append(f"### {inst.category.replace('_', ' ').title()}")
                    prompt_sections.append(inst.instruction)
                    
                    if inst.examples:
                        prompt_sections.append("\n**Examples:**")
                        for example in inst.examples:
                            prompt_sections.append(f"- {example}")
                    
                    if inst.constraints:
                        prompt_sections.append("\n**Constraints:**")
                        for constraint in inst.constraints:
                            prompt_sections.append(f"- {constraint}")
                    
                    if inst.quality_metrics:
                        prompt_sections.append("\n**Quality Metrics:**")
                        for metric in inst.quality_metrics:
                            prompt_sections.append(f"- {metric}")
                    
                    prompt_sections.append("")
        
        return "\n".join(prompt_sections)

# Best Practices for Instruction Tuning
INSTRUCTION_TUNING_BEST_PRACTICES = """
# Best Practices for Multi-Agent Instruction Tuning

## 1. Instruction Hierarchy
- **System Instructions**: Core behavior and role definition
- **Domain Instructions**: Industry/domain-specific knowledge
- **Task Instructions**: Specific task completion guidelines
- **Context Instructions**: Situational adaptations

## 2. Instruction Components
Every instruction should include:
- **Clear directive**: What the agent should do
- **Rationale**: Why this approach is recommended
- **Examples**: Concrete illustrations of good/bad outputs
- **Constraints**: Boundaries and limitations
- **Quality metrics**: How to measure success

## 3. Prompt Engineering Techniques
- **Few-shot learning**: Provide 3-5 examples per instruction
- **Chain-of-thought**: Encourage step-by-step reasoning
- **Role-playing**: Define expertise level and perspective
- **Negative examples**: Show what NOT to do
- **Progressive refinement**: Iterate based on outputs

## 4. Testing and Validation
- **A/B testing**: Compare instruction variations
- **Human evaluation**: Expert review of outputs
- **Automated metrics**: Track KPIs per instruction set
- **Edge case testing**: Unusual scenarios and inputs
- **Consistency checks**: Cross-agent alignment

## 5. Continuous Improvement
- **Feedback loops**: Incorporate user feedback
- **Performance monitoring**: Track instruction effectiveness
- **Version control**: Maintain instruction history
- **Regular audits**: Review and update quarterly
- **Documentation**: Maintain instruction changelog

## 6. Inter-Agent Coordination
- **Shared vocabulary**: Common terms across agents
- **Output standards**: Consistent formatting
- **Handoff protocols**: Clear information passing
- **Conflict resolution**: Priority rules for disagreements
- **Collective goals**: Align individual and system objectives
"""

if __name__ == "__main__":
    # Example usage
    orchestrator = InstructionOrchestrator()
    
    # Get instructions for a promotional campaign
    campaign_context = {
        "campaign_type": "promotional_campaign",
        "industry": "e-commerce",
        "target_audience": "high-value customers",
        "objective": "increase_sales"
    }
    
    instructions = orchestrator.get_instructions_for_campaign(
        campaign_type="promotional_campaign",
        context=campaign_context
    )
    
    # Format for content strategist
    if "content_strategist" in instructions:
        formatted = orchestrator.format_instructions_for_prompt(
            instructions["content_strategist"]
        )
        print("Content Strategist Instructions:")
        print(formatted)