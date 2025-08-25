# Email/SMS Multi-Agent MCP Server

A Model Context Protocol (MCP) server that provides collaborative AI agents for comprehensive email and SMS campaign creation. This system orchestrates multiple specialized agents to create optimized marketing campaigns through intelligent collaboration.

## Architecture

This MCP server implements a multi-agent system similar to the CLAUDE.md pattern, with specialized agents working together to create complete email and SMS campaigns:

### Agent Roles

- **Content Strategist** - Campaign strategy and messaging framework
- **Copywriter** - Subject lines, body copy, and CTAs
- **Designer** - Email templates and visual elements  
- **Segmentation Expert** - Audience targeting and personalization
- **A/B Test Coordinator** - Test design and optimization
- **Compliance Officer** - Legal, deliverability, and brand guidelines
- **Performance Analyst** - Metrics and optimization recommendations

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Add to your Claude Code MCP configuration:
```bash
claude mcp add email-sms-agents --transport stdio -- python /path/to/email-sms-mcp-server/server.py
```

## Usage Examples

### Create Complete Email Campaign

```python
# Request a complete email campaign
{
  "campaign_type": "promotional",
  "target_audience": "high-value customers",
  "objectives": ["increase_sales", "drive_engagement"],
  "brand_guidelines": {
    "tone": "professional",
    "colors": ["#007bff", "#28a745"],
    "fonts": ["Arial", "Helvetica"]
  },
  "customer_data": {
    "segments": ["vip_customers", "recent_purchasers"],
    "personalization_fields": ["first_name", "location", "purchase_history"]
  }
}
```

### Create SMS Campaign

```python
# Request an SMS campaign
{
  "campaign_type": "flash_sale",
  "target_audience": "mobile_engaged_users", 
  "objectives": ["urgent_action", "limited_time_offer"],
  "character_limit": 160
}
```

### Consult Individual Agent

```python
# Get copywriting assistance
{
  "agent_name": "copywriter",
  "request": {
    "content_type": "email",
    "strategy": {
      "primary_message": "Exclusive summer sale",
      "tone": "urgent_but_friendly"
    },
    "requirements": ["mobile_optimized", "high_conversion"]
  }
}
```

## Available Tools

### `create_email_campaign`
Creates a complete email campaign using multi-agent collaboration.

**Parameters:**
- `campaign_type` (required): Type of campaign (promotional, newsletter, transactional)
- `target_audience` (required): Target audience description
- `objectives`: Array of campaign objectives
- `brand_guidelines`: Brand guidelines and constraints
- `customer_data`: Available customer data for personalization

### `create_sms_campaign`
Creates an SMS campaign using multi-agent collaboration.

**Parameters:**
- `campaign_type` (required): Type of SMS campaign
- `target_audience` (required): Target audience description  
- `objectives`: Campaign objectives
- `character_limit`: SMS character limit (default: 160)

### `consult_agent`
Consults a specific agent for specialized expertise.

**Parameters:**
- `agent_name` (required): Name of agent to consult
- `request` (required): Request parameters for the specific agent

## Workflow Process

1. **Strategy Development** (Content Strategist)
   - Analyzes campaign requirements
   - Develops messaging framework
   - Sets strategic direction

2. **Copy Creation** (Copywriter)
   - Creates subject line variants
   - Writes compelling body copy
   - Optimizes calls-to-action
   - Implements personalization

3. **Design Specifications** (Designer)
   - Designs email templates
   - Ensures brand consistency
   - Optimizes visual hierarchy
   - Creates responsive layouts

4. **Audience Targeting** (Segmentation Expert)
   - Identifies optimal segments
   - Creates personalization rules
   - Optimizes send timing
   - Sets frequency caps

5. **Compliance Review** (Compliance Officer)
   - Ensures legal compliance
   - Reviews brand guidelines
   - Checks deliverability factors

6. **A/B Testing** (A/B Test Coordinator)
   - Designs test framework
   - Creates test hypotheses
   - Defines success metrics

7. **Performance Prediction** (Performance Analyst)
   - Predicts campaign metrics
   - Provides optimization recommendations
   - Sets benchmarks

## Output Structure

Each campaign creation returns:

```json
{
  "campaign_creation_complete": true,
  "workflow_results": {
    "strategy": { /* Strategic framework */ },
    "copy": { /* Copy elements and variants */ },
    "design": { /* Visual specifications */ },
    "segmentation": { /* Targeting strategy */ }
  },
  "final_recommendations": [
    "Implementation steps",
    "Testing recommendations", 
    "Performance monitoring"
  ]
}
```

## Integration with Existing Systems

This MCP server is designed to integrate with:

- **Klaviyo API** - Campaign deployment and audience management
- **Email Testing Tools** - Template testing and deliverability
- **Analytics Platforms** - Performance tracking and optimization
- **Design Tools** - Asset creation and brand consistency

## Claude Code Integration

When connected to Claude Code, you can:

```bash
# Create email campaign
create_email_campaign campaign_type:"promotional" target_audience:"high-value customers"

# Get copywriting help
consult_agent agent_name:"copywriter" request:'{...}'

# Create SMS campaign  
create_sms_campaign campaign_type:"flash_sale" target_audience:"mobile_users"
```

## Advanced Features

### Context Sharing
Agents share context throughout the workflow, ensuring consistency and building upon each other's outputs.

### Specialization
Each agent has deep expertise in their domain, providing specialized insights and recommendations.

### Orchestration
The system automatically manages agent collaboration, ensuring optimal workflow execution.

### Extensibility
New agents can be easily added to extend system capabilities.

## Development

To extend the system:

1. Create new agent classes inheriting from `EmailSMSAgent`
2. Implement the `process_request` method
3. Add agent to the `MultiAgentOrchestrator`
4. Update configuration and workflows

## Configuration

Agent roles and workflows are defined in `agents_config.json`. Modify this file to:
- Add new agent specializations
- Customize workflow steps
- Update collaboration patterns
- Define integration points

This multi-agent system brings the power of specialized AI collaboration to email and SMS campaign creation, ensuring comprehensive, optimized campaigns through intelligent agent coordination.