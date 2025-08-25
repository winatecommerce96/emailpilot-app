"""
Ingest node: Validates and prepares input data for the calendar planning workflow
"""
from typing import Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class CalendarInputs(BaseModel):
    """Validated input model for calendar planning"""
    brand: str = Field(..., min_length=1, description="Brand/client name")
    month: str = Field(..., regex=r'^\d{4}-\d{2}$', description="Target month (YYYY-MM)")
    client_sales_goal: float = Field(..., gt=0, description="Monthly revenue target")
    affinity_segment_1_name: str = Field(..., description="Primary customer segment")
    affinity_segment_2_name: str = Field(..., description="Secondary segment")
    affinity_segment_3_name: str = Field(default="", description="Optional tertiary segment")
    key_growth_objective: str = Field(..., description="Primary business goal")
    key_dates: Dict[str, Any] = Field(default_factory=dict, description="Promotional dates")
    unengaged_segment_size: int = Field(default=0, ge=0, description="Size of at-risk customers")
    
    @validator('month')
    def validate_month(cls, v):
        """Ensure month is valid and not in the past"""
        try:
            month_date = datetime.strptime(v, '%Y-%m')
            current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_date < current_month:
                logger.warning(f"Month {v} is in the past")
        except ValueError:
            raise ValueError(f"Invalid month format: {v}")
        return v


def run(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ingest and validate inputs for calendar planning
    
    Args:
        state: Current workflow state
        
    Returns:
        Updated state with validated inputs
    """
    try:
        # Extract raw inputs
        raw_inputs = state.get('inputs', {})
        
        # If brand and month are at top level, use them
        if 'brand' in state and 'month' in state:
            raw_inputs['brand'] = state['brand']
            raw_inputs['month'] = state['month']
        
        # Validate inputs using Pydantic
        validated = CalendarInputs(**raw_inputs)
        
        # Update state with validated data
        state['brand'] = validated.brand
        state['month'] = validated.month
        state['inputs'] = validated.dict()
        state['errors'] = []
        
        # Add metadata
        if 'run_id' not in state:
            state['run_id'] = str(uuid.uuid4())
        
        # Initialize other state fields
        state['candidates'] = []
        state['calendar'] = {}
        state['valid'] = False
        state['approvals'] = {}
        
        logger.info(f"Ingested inputs for {validated.brand} - {validated.month}")
        logger.debug(f"Validated inputs: {validated.dict()}")
        
        return state
        
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        state['errors'] = state.get('errors', []) + [f"Ingest error: {str(e)}"]
        state['valid'] = False
        return state