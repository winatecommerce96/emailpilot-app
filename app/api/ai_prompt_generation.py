"""
AI-Powered Prompt Generation Service
Generates intelligent prompts with automatic variable discovery and injection
"""

from fastapi import APIRouter, HTTPException, Depends, Body
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional, Literal
import logging
import json
import re
from datetime import datetime

# LangChain imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai-prompts"])

# Variable patterns for different contexts
VARIABLE_PATTERNS = {
    "email": [
        "{client_name}", "{campaign_type}", "{segment}", "{subject_line}",
        "{send_time}", "{list_name}", "{template_id}", "{preview_text}"
    ],
    "analytics": [
        "{time_period}", "{metrics}", "{revenue_goal}", "{conversion_rate}",
        "{start_date}", "{end_date}", "{comparison_period}", "{kpi_targets}"
    ],
    "planning": [
        "{selected_month}", "{client_sales_goal}", "{campaign_count}",
        "{affinity_segment_1_name}", "{affinity_segment_2_name}",
        "{key_growth_objective}", "{holiday_dates}"
    ],
    "creative": [
        "{brand_voice}", "{content_type}", "{target_audience}",
        "{product_focus}", "{cta_text}", "{tone}", "{word_count}"
    ],
    "general": [
        "{client_id}", "{user_input}", "{context}", "{task}",
        "{output_format}", "{language}", "{max_length}"
    ]
}

# Agent type to variable mapping
AGENT_VARIABLES = {
    "email": ["client", "campaign", "segmentation", "timing"],
    "analytics": ["metrics", "performance", "goals", "reporting"],
    "planning": ["calendar", "strategy", "growth", "seasonal"],
    "creative": ["brand", "content", "messaging", "design"],
    "general": ["basic", "context", "task", "format"]
}

class PromptGenerationRequest(BaseModel):
    """Request model for AI prompt generation"""
    type: Literal["agent", "workflow"] = Field(..., description="Type of prompt to generate")
    description: str = Field(..., description="Natural language description of desired functionality")
    agent_type: Optional[str] = Field(default="general", description="Type of agent (for agent prompts)")
    workflow_type: Optional[str] = Field(default="sequential", description="Type of workflow (for workflow prompts)")
    include_variables: bool = Field(default=True, description="Whether to include variables")
    client_id: Optional[str] = Field(default=None, description="Optional client ID for context")
    llm: str = Field(default="gemini", description="LLM to use: gemini, gpt-4, claude")

class PromptEnhanceRequest(BaseModel):
    """Request model for prompt enhancement"""
    prompt: str = Field(..., description="Existing prompt to enhance")
    agent_type: str = Field(default="general", description="Type of agent")
    suggest_variables: bool = Field(default=True, description="Whether to suggest new variables")
    fix_syntax: bool = Field(default=True, description="Fix variable syntax issues")
    optimize_structure: bool = Field(default=True, description="Optimize prompt structure")

class VariableSuggestionRequest(BaseModel):
    """Request model for variable suggestions"""
    prompt: str = Field(..., description="Prompt text to analyze")
    agent_type: str = Field(default="general", description="Type of agent")
    existing_variables: List[str] = Field(default=[], description="Variables already in use")

class PromptGenerationResponse(BaseModel):
    """Response model for prompt generation"""
    success: bool
    prompt: str
    variables: List[Dict[str, Any]]
    explanation: str
    metadata: Dict[str, Any]

class PromptEnhanceResponse(BaseModel):
    """Response model for prompt enhancement"""
    success: bool
    enhanced_prompt: str
    added_variables: List[str]
    removed_variables: List[str]
    fixes_applied: List[str]
    confidence: float

class VariableSuggestionResponse(BaseModel):
    """Response model for variable suggestions"""
    success: bool
    suggested_variables: List[Dict[str, Any]]
    rationale: str

def get_llm(llm_type: str = None, temperature: float = 0.7, model: str = None):
    """Get the appropriate LLM based on selection with latest models"""
    # Import the secrets module to get API keys from Secret Manager
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "multi-agent"))
    from integrations.langchain_core.secrets import get_api_key
    
    # Map model IDs to providers if a specific model is provided
    model_to_provider = {
        # OpenAI models
        'gpt-4o-mini': 'openai',
        'gpt-4o': 'openai',
        'o1-preview': 'openai',
        # Anthropic models
        'claude-3-5-haiku-20241022': 'anthropic',
        'claude-3-5-sonnet-20241022': 'anthropic',
        'claude-3-opus-20240229': 'anthropic',
        # Google models
        'gemini-1.5-flash-002': 'gemini',
        'gemini-1.5-pro-002': 'gemini',
        'gemini-2.0-flash-exp': 'gemini'
    }
    
    # If a specific model is provided, determine the provider
    if model and model in model_to_provider:
        llm_type = model_to_provider[model]
    
    # Default models for each provider (Better tier)
    default_models = {
        "openai": "gpt-4o",
        "gpt-4": "gpt-4o",  # Map old name to new
        "anthropic": "claude-3-5-sonnet-20241022",
        "claude": "claude-3-5-sonnet-20241022",  # Map old name to new
        "gemini": "gemini-1.5-pro-002",
        "google": "gemini-1.5-pro-002"  # Alternative name
    }
    
    # Normalize llm_type and get the appropriate model
    llm_type = llm_type or "openai"
    model_name = model or default_models.get(llm_type, "gpt-4o")
    
    # Determine the actual provider
    if llm_type in ["openai", "gpt-4"]:
        api_key = get_api_key("openai")
        if not api_key:
            raise ValueError("OpenAI API key not configured in Secret Manager")
        return ChatOpenAI(model=model_name, temperature=temperature, api_key=api_key)
    elif llm_type in ["anthropic", "claude"]:
        api_key = get_api_key("anthropic")
        if not api_key:
            raise ValueError("Anthropic API key not configured in Secret Manager")
        return ChatAnthropic(model=model_name, temperature=temperature, anthropic_api_key=api_key)
    else:  # Default to Gemini for "gemini", "google", or unknown
        api_key = get_api_key("gemini")
        if not api_key:
            raise ValueError("Google API key not configured in Secret Manager")
        # Gemini models need simplified names for the API
        gemini_model = model_name.replace("-002", "").replace("-exp", "")
        return ChatGoogleGenerativeAI(model=gemini_model, temperature=temperature, google_api_key=api_key)

def extract_variables_from_text(text: str) -> List[str]:
    """Extract variables from prompt text using regex"""
    # Match {variable_name} pattern
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'
    matches = re.findall(pattern, text)
    return list(set(matches))  # Return unique variables

def suggest_variables_for_context(agent_type: str, prompt_text: str) -> List[str]:
    """Suggest variables based on agent type and prompt content"""
    suggested = []
    
    # Get base variables for agent type
    if agent_type in VARIABLE_PATTERNS:
        suggested.extend(VARIABLE_PATTERNS[agent_type])
    
    # Add general variables
    suggested.extend(VARIABLE_PATTERNS["general"][:3])  # Add some general ones
    
    # Context-specific additions based on keywords
    prompt_lower = prompt_text.lower()
    
    if "revenue" in prompt_lower or "sales" in prompt_lower:
        suggested.extend(["{revenue_goal}", "{mtd_revenue}", "{conversion_rate}"])
    
    if "campaign" in prompt_lower:
        suggested.extend(["{campaign_name}", "{campaign_type}", "{send_date}"])
    
    if "segment" in prompt_lower or "audience" in prompt_lower:
        suggested.extend(["{segment_name}", "{segment_size}", "{segment_criteria}"])
    
    if "month" in prompt_lower or "calendar" in prompt_lower:
        suggested.extend(["{selected_month}", "{month_name}", "{days_in_month}"])
    
    if "goal" in prompt_lower or "target" in prompt_lower:
        suggested.extend(["{target_metric}", "{current_value}", "{goal_value}"])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggested = []
    for var in suggested:
        if var not in seen:
            seen.add(var)
            unique_suggested.append(var)
    
    return unique_suggested

@router.post("/generate-prompt", response_model=PromptGenerationResponse)
async def generate_prompt(request: PromptGenerationRequest):
    """
    Generate an intelligent prompt with automatic variable discovery
    """
    try:
        logger.info(f"Generating {request.type} prompt: {request.description[:100]}...")
        
        # Get LLM
        llm = get_llm(request.llm, temperature=0.7)
        
        # Build generation prompt based on type
        if request.type == "agent":
            system_prompt = """You are an expert at creating AI agent system prompts.
Generate a comprehensive, well-structured prompt for an agent with these requirements:

Description: {description}
Agent Type: {agent_type}
Include Variables: {include_variables}

Guidelines:
1. Start with a clear role definition
2. Include specific capabilities and knowledge
3. Add variables using {variable_name} syntax for dynamic content
4. Include behavioral instructions and constraints
5. End with output format specifications

Relevant variables for {agent_type} agents:
{suggested_variables}

Generate a prompt that is:
- Clear and specific
- Uses appropriate variables for the context
- Follows best practices for LLM prompting
- Includes all necessary context and constraints

Format your response as JSON with keys:
- prompt: The complete system prompt
- variables: Array of {name, description, type, required} objects
- explanation: Brief explanation of the prompt structure"""
        else:  # workflow
            system_prompt = """You are an expert at creating workflow descriptions.
Generate a comprehensive workflow prompt with these requirements:

Description: {description}
Workflow Type: {workflow_type}
Include Variables: {include_variables}

Guidelines:
1. Define clear workflow objectives
2. Specify input and output requirements
3. Add variables using {variable_name} syntax for parameters
4. Include step-by-step logic flow
5. Define success criteria and error handling

Generate a workflow prompt that is:
- Structured and logical
- Uses appropriate variables for parameterization
- Includes necessary tools and agents
- Defines clear success metrics

Format your response as JSON with keys:
- prompt: The complete workflow description
- variables: Array of {name, description, type, required} objects
- explanation: Brief explanation of the workflow structure"""
        
        # Get suggested variables
        agent_type = request.agent_type or "general"
        suggested_vars = suggest_variables_for_context(agent_type, request.description)
        
        # Create the prompt
        prompt_template = ChatPromptTemplate.from_template(system_prompt)
        
        # Generate the prompt
        messages = prompt_template.format_messages(
            description=request.description,
            agent_type=agent_type,
            workflow_type=request.workflow_type,
            include_variables=request.include_variables,
            suggested_variables=", ".join(suggested_vars[:10])  # Limit suggestions
        )
        
        response = llm.invoke(messages)
        
        # Parse response
        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            # Fallback parsing
            result = {
                "prompt": response.content,
                "variables": [],
                "explanation": "Generated prompt (parsing failed)"
            }
        
        # Ensure all expected keys exist
        prompt_text = result.get("prompt", "")
        variables = result.get("variables", [])
        explanation = result.get("explanation", "")
        
        # Extract any additional variables from the generated prompt
        extracted_vars = extract_variables_from_text(prompt_text)
        
        # Ensure all extracted variables are in the variables list
        variable_names = {v.get("name", "") for v in variables}
        for var in extracted_vars:
            if var not in variable_names:
                variables.append({
                    "name": var,
                    "description": f"Auto-detected variable: {var}",
                    "type": "string",
                    "required": False
                })
        
        return PromptGenerationResponse(
            success=True,
            prompt=prompt_text,
            variables=variables,
            explanation=explanation,
            metadata={
                "type": request.type,
                "agent_type": agent_type,
                "llm_used": request.llm,
                "timestamp": datetime.now().isoformat()
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/enhance-prompt", response_model=PromptEnhanceResponse)
async def enhance_prompt(request: PromptEnhanceRequest):
    """
    Enhance an existing prompt with intelligent variable suggestions
    """
    try:
        logger.info(f"Enhancing prompt for {request.agent_type} agent")
        
        # Get LLM
        llm = get_llm("gemini", temperature=0.5)  # Lower temp for enhancement
        
        # Extract current variables
        current_vars = extract_variables_from_text(request.prompt)
        
        # Get suggested variables
        suggested_vars = suggest_variables_for_context(request.agent_type, request.prompt)
        
        # Find missing beneficial variables
        missing_vars = [v for v in suggested_vars if v.replace("{", "").replace("}", "") not in current_vars]
        
        # Build enhancement prompt
        enhancement_prompt = """Enhance this agent prompt by:
1. Adding relevant variables from the suggested list where appropriate
2. Fixing any syntax issues with existing variables
3. Improving structure and clarity
4. Ensuring consistency in variable usage

Current Prompt:
{current_prompt}

Current Variables: {current_vars}
Suggested Additional Variables: {missing_vars}
Agent Type: {agent_type}

Rules:
- Preserve the original intent and meaning
- Only add variables where they make sense
- Use proper {variable_name} syntax
- Keep the prompt concise but comprehensive

Return JSON with:
- enhanced_prompt: The improved prompt
- added_variables: List of variables added
- fixes_applied: List of fixes made"""
        
        # Create the prompt
        prompt_template = ChatPromptTemplate.from_template(enhancement_prompt)
        
        messages = prompt_template.format_messages(
            current_prompt=request.prompt,
            current_vars=", ".join(current_vars),
            missing_vars=", ".join(missing_vars[:8]),  # Limit to prevent overload
            agent_type=request.agent_type
        )
        
        response = llm.invoke(messages)
        
        # Parse response
        try:
            result = json.loads(response.content)
            enhanced_prompt = result.get("enhanced_prompt", request.prompt)
            added_variables = result.get("added_variables", [])
            fixes_applied = result.get("fixes_applied", [])
        except:
            # Fallback: just fix syntax
            enhanced_prompt = request.prompt
            added_variables = []
            fixes_applied = []
            
            if request.fix_syntax:
                # Basic syntax fixing
                enhanced_prompt = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', enhanced_prompt)
                enhanced_prompt = re.sub(r'\[([a-zA-Z_][a-zA-Z0-9_]*)\]', r'{\1}', enhanced_prompt)
                if enhanced_prompt != request.prompt:
                    fixes_applied.append("Fixed variable syntax")
        
        # Calculate confidence
        confidence = 0.8 if added_variables or fixes_applied else 0.5
        
        return PromptEnhanceResponse(
            success=True,
            enhanced_prompt=enhanced_prompt,
            added_variables=added_variables,
            removed_variables=[],
            fixes_applied=fixes_applied,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Error enhancing prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/suggest-variables", response_model=VariableSuggestionResponse)
async def suggest_variables(request: VariableSuggestionRequest):
    """
    Suggest relevant variables for a given prompt and context
    """
    try:
        logger.info(f"Suggesting variables for {request.agent_type} agent")
        
        # Get contextual suggestions
        suggested = suggest_variables_for_context(request.agent_type, request.prompt)
        
        # Filter out existing variables
        existing = set(request.existing_variables)
        new_suggestions = [v for v in suggested if v not in existing]
        
        # Build detailed variable info
        variable_info = []
        for var in new_suggestions[:10]:  # Limit to top 10
            var_name = var.replace("{", "").replace("}", "")
            variable_info.append({
                "name": var_name,
                "syntax": var,
                "description": f"Variable for {var_name.replace('_', ' ')}",
                "type": "string",  # Default type
                "category": request.agent_type,
                "usage_example": f"Use {var} to reference the {var_name.replace('_', ' ')}"
            })
        
        # Generate rationale
        rationale = f"Based on the {request.agent_type} agent type and prompt content, "
        rationale += f"suggested {len(variable_info)} variables that would enhance functionality. "
        rationale += "These variables enable dynamic content and improve reusability."
        
        return VariableSuggestionResponse(
            success=True,
            suggested_variables=variable_info,
            rationale=rationale
        )
        
    except Exception as e:
        logger.error(f"Error suggesting variables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/variable-categories")
async def get_variable_categories():
    """
    Get all available variable categories and patterns
    """
    return {
        "categories": list(VARIABLE_PATTERNS.keys()),
        "patterns": VARIABLE_PATTERNS,
        "agent_mappings": AGENT_VARIABLES
    }

@router.post("/validate-variables")
async def validate_variables(prompt: str = Body(..., embed=True)):
    """
    Validate variables in a prompt
    """
    try:
        # Extract variables
        variables = extract_variables_from_text(prompt)
        
        # Check for common issues
        issues = []
        
        # Check for empty variables
        if "{}" in prompt:
            issues.append("Empty variable brackets found")
        
        # Check for malformed variables
        if "{{" in prompt and "}}" in prompt:
            issues.append("Double brackets found - use single brackets")
        
        # Check for common typos
        common_vars = ["client_name", "client_id", "user_input", "context"]
        for var in variables:
            if var.lower() in [cv.lower() for cv in common_vars] and var not in common_vars:
                issues.append(f"Possible typo: {var} (did you mean {var.lower()}?)")
        
        return {
            "valid": len(issues) == 0,
            "variables": variables,
            "issues": issues,
            "count": len(variables)
        }
        
    except Exception as e:
        logger.error(f"Error validating variables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))