# AI Orchestrator Integration Examples

This document provides real-world examples of integrating the AI Orchestrator into various EmailPilot components.

## Table of Contents
1. [Email Campaign Generator](#email-campaign-generator)
2. [Report Generation](#report-generation)
3. [Goal Setting Assistant](#goal-setting-assistant)
4. [Performance Analysis](#performance-analysis)
5. [Calendar Planning AI](#calendar-planning-ai)
6. [Multi-Agent Coordination](#multi-agent-coordination)

## Email Campaign Generator

Generate email campaigns with automatic marketing content optimization:

```python
# app/services/campaign_generator.py
from app.core.ai_orchestrator import get_ai_orchestrator

class CampaignGenerator:
    def __init__(self):
        self.orchestrator = get_ai_orchestrator()
    
    async def generate_campaign(
        self,
        product: str,
        audience: str,
        tone: str,
        promotion: str = None
    ):
        """Generate complete email campaign"""
        
        # Build the prompt
        prompt = f"""
        Create an email marketing campaign for:
        Product: {product}
        Target Audience: {audience}
        Tone: {tone}
        {'Promotion: ' + promotion if promotion else ''}
        
        Include:
        1. Subject line (3 variations)
        2. Preview text
        3. Email body with HTML structure
        4. Call-to-action button text
        5. Footer disclaimer
        """
        
        # Orchestrator automatically detects marketing content
        # and routes to Gemini 2.0 Flash to avoid safety filters
        response = await self.orchestrator.complete({
            "messages": [{"role": "user", "content": prompt}],
            "provider": "auto",  # Will select Gemini for marketing
            "temperature": 0.8,  # Higher creativity
            "max_tokens": 2000
        })
        
        return {
            "campaign_content": response.content,
            "provider_used": response.provider,
            "model_used": response.model,
            "tokens_used": response.usage
        }

# Usage in API endpoint
from fastapi import APIRouter
router = APIRouter()

@router.post("/api/campaigns/generate")
async def generate_campaign(request: dict):
    generator = CampaignGenerator()
    return await generator.generate_campaign(
        product=request["product"],
        audience=request["audience"],
        tone=request["tone"],
        promotion=request.get("promotion")
    )
```

## Report Generation

Generate comprehensive performance reports with data analysis:

```python
# app/services/report_generator.py
from app.core.ai_orchestrator import ai_complete
from typing import Dict, Any

class ReportGenerator:
    async def generate_weekly_report(
        self,
        client_data: Dict[str, Any]
    ):
        """Generate weekly performance report"""
        
        # Prepare data summary
        metrics_summary = f"""
        Client: {client_data['name']}
        Period: {client_data['start_date']} to {client_data['end_date']}
        
        Metrics:
        - Total Revenue: ${client_data['revenue']:,.2f}
        - Orders: {client_data['orders']}
        - Conversion Rate: {client_data['conversion_rate']:.2%}
        - Email Opens: {client_data['email_opens']}
        - Click Rate: {client_data['click_rate']:.2%}
        
        Top Campaigns:
        {self._format_campaigns(client_data['top_campaigns'])}
        """
        
        # Generate insights using orchestrator
        insights = await ai_complete(
            messages=[
                {"role": "system", "content": "You are a marketing analytics expert."},
                {"role": "user", "content": f"""
                Analyze this weekly performance data and provide:
                1. Key insights (3-5 bullet points)
                2. Performance trends
                3. Recommendations for improvement
                4. Action items for next week
                
                Data:
                {metrics_summary}
                """}
            ],
            provider="openai",  # Use GPT-4 for analytical tasks
            model="gpt-4o",
            temperature=0.3,  # Lower temperature for factual analysis
            max_tokens=1500
        )
        
        return {
            "report_date": datetime.now().isoformat(),
            "client": client_data['name'],
            "metrics": metrics_summary,
            "ai_insights": insights,
            "status": "completed"
        }
    
    def _format_campaigns(self, campaigns):
        return "\n".join([
            f"  - {c['name']}: ${c['revenue']:,.2f} ({c['orders']} orders)"
            for c in campaigns[:5]
        ])
```

## Goal Setting Assistant

AI-powered goal recommendations based on historical performance:

```python
# app/services/goal_assistant.py
from app.core.ai_orchestrator import get_ai_orchestrator, CompletionRequest

class GoalSettingAssistant:
    def __init__(self):
        self.orchestrator = get_ai_orchestrator()
    
    async def suggest_goals(
        self,
        historical_data: dict,
        business_context: str
    ):
        """Suggest SMART goals based on data"""
        
        request = CompletionRequest(
            messages=[
                {"role": "system", "content": 
                 "You are a business strategy consultant specializing in e-commerce KPIs."},
                {"role": "user", "content": f"""
                Based on the following historical performance, suggest 5 SMART goals:
                
                Historical Data:
                - Average Monthly Revenue: ${historical_data['avg_revenue']:,.2f}
                - Growth Rate: {historical_data['growth_rate']:.1%}
                - Best Month: ${historical_data['best_month']:,.2f}
                - Current Trajectory: {historical_data['trajectory']}
                
                Business Context: {business_context}
                
                Format each goal as:
                - Goal: [specific metric and target]
                - Timeline: [specific timeframe]
                - Rationale: [why this goal makes sense]
                - Action Steps: [2-3 concrete steps]
                """}
            ],
            provider="claude",  # Use Claude for strategic planning
            model="claude-3-5-sonnet-20241022",
            temperature=0.6,
            max_tokens=2000
        )
        
        response = await self.orchestrator.complete(request)
        
        # Parse and structure the response
        return self._parse_goals(response.content)
    
    def _parse_goals(self, content: str):
        """Parse AI response into structured goals"""
        # Implementation to parse the text into structured data
        goals = []
        # ... parsing logic ...
        return goals
```

## Performance Analysis

Real-time performance monitoring with AI insights:

```python
# app/services/performance_monitor.py
from app.core.ai_orchestrator import ai_complete, ai_stream

class PerformanceMonitor:
    async def analyze_anomaly(
        self,
        metric_name: str,
        current_value: float,
        expected_value: float,
        context: dict
    ):
        """Analyze performance anomalies"""
        
        # Quick analysis for urgent issues
        if abs(current_value - expected_value) / expected_value > 0.5:
            # Use fast model for urgent alerts
            model_tier = "fast"
        else:
            # Use standard model for routine analysis
            model_tier = "standard"
        
        analysis = await ai_complete(
            messages=[{
                "role": "user",
                "content": f"""
                Analyze this performance anomaly:
                
                Metric: {metric_name}
                Current: {current_value}
                Expected: {expected_value}
                Deviation: {((current_value - expected_value) / expected_value * 100):.1f}%
                
                Context:
                - Time: {context['timestamp']}
                - Client: {context['client']}
                - Recent Events: {context.get('recent_events', 'None')}
                
                Provide:
                1. Likely cause
                2. Impact assessment
                3. Recommended action
                """
            }],
            provider="auto",
            model_tier=model_tier,
            temperature=0.3,
            max_tokens=500
        )
        
        return {
            "anomaly_detected": True,
            "metric": metric_name,
            "severity": self._calculate_severity(current_value, expected_value),
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        }
    
    async def stream_analysis(self, data: dict):
        """Stream real-time analysis"""
        async for chunk in ai_stream(
            messages=[{"role": "user", "content": f"Analyze: {data}"}],
            provider="gemini",
            model="gemini-1.5-flash-002"
        ):
            yield chunk
```

## Calendar Planning AI

Intelligent campaign scheduling with AI assistance:

```python
# app/services/calendar_planning.py
from app.core.ai_orchestrator import get_ai_orchestrator

class CalendarPlanningAI:
    def __init__(self):
        self.orchestrator = get_ai_orchestrator()
    
    async def suggest_campaign_schedule(
        self,
        business_type: str,
        target_month: str,
        existing_campaigns: list,
        goals: dict
    ):
        """Suggest optimal campaign schedule"""
        
        prompt = f"""
        Create a campaign calendar for:
        Business: {business_type}
        Month: {target_month}
        
        Current Campaigns: {len(existing_campaigns)}
        Revenue Goal: ${goals.get('revenue', 0):,.2f}
        
        Existing Schedule:
        {self._format_campaigns(existing_campaigns)}
        
        Suggest:
        1. Optimal days for new campaigns
        2. Campaign themes aligned with seasonal trends
        3. Estimated impact on revenue goal
        4. Content ideas for each suggested campaign
        
        Consider:
        - Industry best practices
        - Seasonal patterns
        - Avoiding campaign fatigue
        - Maximizing engagement
        """
        
        response = await self.orchestrator.complete({
            "messages": [
                {"role": "system", "content": 
                 "You are a marketing calendar expert with deep knowledge of e-commerce seasonality."},
                {"role": "user", "content": prompt}
            ],
            "model_tier": "flagship",  # Use best model for planning
            "temperature": 0.7,
            "max_tokens": 2500
        })
        
        return self._parse_schedule(response.content)
```

## Multi-Agent Coordination

Coordinate multiple AI agents for complex tasks:

```python
# app/services/multi_agent_coordinator.py
from app.core.ai_orchestrator import get_ai_orchestrator
import asyncio

class MultiAgentCoordinator:
    def __init__(self):
        self.orchestrator = get_ai_orchestrator()
    
    async def execute_campaign_workflow(
        self,
        campaign_brief: dict
    ):
        """Execute full campaign creation with multiple agents"""
        
        # Step 1: Strategy Agent
        strategy = await self._run_agent(
            "strategist",
            f"Develop strategy for: {campaign_brief}",
            provider="claude"  # Claude for strategy
        )
        
        # Step 2: Creative Agent
        creative = await self._run_agent(
            "creative",
            f"Create concepts based on strategy: {strategy}",
            provider="openai"  # GPT-4 for creative
        )
        
        # Step 3: Copywriting Agent
        copy = await self._run_agent(
            "copywriter",
            f"Write copy for concepts: {creative}",
            provider="gemini"  # Gemini for marketing copy
        )
        
        # Step 4: Review Agent
        review = await self._run_agent(
            "reviewer",
            f"Review and optimize: {copy}",
            provider="claude"  # Claude for review
        )
        
        return {
            "strategy": strategy,
            "creative": creative,
            "copy": copy,
            "review": review,
            "status": "completed"
        }
    
    async def _run_agent(
        self,
        agent_role: str,
        task: str,
        provider: str
    ):
        """Run individual agent task"""
        
        response = await self.orchestrator.complete({
            "messages": [
                {"role": "system", 
                 "content": f"You are a {agent_role} agent in a marketing team."},
                {"role": "user", "content": task}
            ],
            "provider": provider,
            "temperature": 0.7,
            "max_tokens": 1500
        })
        
        return response.content
    
    async def parallel_analysis(
        self,
        data: dict,
        analysis_types: list
    ):
        """Run multiple analyses in parallel"""
        
        tasks = []
        for analysis_type in analysis_types:
            task = self.orchestrator.complete({
                "messages": [{
                    "role": "user",
                    "content": f"Perform {analysis_type} analysis on: {data}"
                }],
                "provider": "auto",
                "model_tier": "fast",  # Use fast models for parallel work
                "max_tokens": 500
            })
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        return {
            analysis_types[i]: results[i].content
            for i in range(len(analysis_types))
        }
```

## Testing Examples

### Unit Test Example

```python
# tests/test_orchestrator_integration.py
import pytest
from app.core.ai_orchestrator import get_ai_orchestrator

@pytest.mark.asyncio
async def test_campaign_generation():
    orchestrator = get_ai_orchestrator()
    
    response = await orchestrator.complete({
        "messages": [{
            "role": "user",
            "content": "Generate email subject for summer sale"
        }],
        "provider": "auto",
        "max_tokens": 100
    })
    
    assert response.content
    assert len(response.content) > 10
    assert response.provider in ["openai", "claude", "gemini"]

@pytest.mark.asyncio  
async def test_fallback_chain():
    orchestrator = get_ai_orchestrator()
    
    # Force a provider that might fail
    response = await orchestrator.complete({
        "messages": [{"role": "user", "content": "Test"}],
        "provider": "claude",
        "model": "invalid-model-xxx"
    })
    
    # Should fallback to working provider
    assert response.content
    assert response.warnings  # Should have fallback warning
```

### Integration Test

```python
# tests/test_api_integration.py
import httpx
import pytest

@pytest.mark.asyncio
async def test_orchestrator_api():
    async with httpx.AsyncClient() as client:
        # Test completion endpoint
        response = await client.post(
            "http://localhost:8000/api/ai/complete",
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "auto",
                "temperature": 0.5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["content"]
        
        # Test model listing
        response = await client.get(
            "http://localhost:8000/api/ai/models"
        )
        
        assert response.status_code == 200
        models = response.json()
        assert "openai" in models["models"]
        assert "gemini" in models["models"]
```

## Best Practices

1. **Provider Selection**:
   - Use `"auto"` for general tasks
   - Use `"gemini"` explicitly for marketing content
   - Use `"claude"` for complex reasoning
   - Use `"openai"` for balanced performance

2. **Model Tiers**:
   - `"flagship"` - Best quality, higher cost
   - `"standard"` - Balanced quality/cost
   - `"fast"` - Quick responses, lower cost

3. **Temperature Settings**:
   - 0.0-0.3: Factual, consistent (analysis, data)
   - 0.4-0.7: Balanced (general tasks)
   - 0.8-1.0: Creative (marketing, brainstorming)

4. **Token Optimization**:
   - Set appropriate `max_tokens` for your use case
   - Use caching for repeated queries
   - Batch similar requests when possible

5. **Error Handling**:
   - Always handle the response properly
   - Check for `warnings` in response
   - Log provider/model used for debugging