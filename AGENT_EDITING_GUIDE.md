# How to Edit Agent Instructions

## Quick Answer
Edit the agent personas directly in `/copywriting/main.py` in the `get_agent_enhancements()` function, starting at line 808.

## Method 1: Direct Code Edit (Currently Active)

### Location
`/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/copywriting/main.py`

### Find the Agent Definitions (Line 808+)
```python
agent_personas = {
    "email_marketing_expert": {
        "role": "email marketing specialist with 10+ years experience",
        "focus": "engagement optimization, subject line psychology, and conversion-driven copy",
        "style": "Use psychological triggers, power words, and emotional appeals. Focus on benefits over features.",
        "techniques": ["urgency creation", "social proof", "FOMO tactics", "personalization strategies"]
    },
    # ... other agents
}
```

### How to Edit

1. **Open the file**:
```bash
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/copywriting
nano main.py  # or use your preferred editor
# Go to line 808 or search for "agent_personas"
```

2. **Modify any agent's instructions**:
```python
"email_marketing_expert": {
    "role": "email marketing specialist with 10+ years experience",  # Change role
    "focus": "YOUR NEW FOCUS HERE",  # Change what they focus on
    "style": "YOUR NEW WRITING STYLE INSTRUCTIONS",  # Change how they write
    "techniques": ["technique1", "technique2", "technique3"]  # Change techniques
},
```

3. **Save and restart the service**:
```bash
# The service auto-reloads if running with --reload flag
# Or manually restart:
pkill -f "uvicorn.*8002"
cd copywriting && uvicorn main:app --port 8002 --reload
```

## Method 2: Frontend UI (Future - Not Yet Connected)

The Admin Panel has an interface for editing agents, but it's not yet connected to the actual generation. Here's where it would be:

### Location
1. Navigate to: http://localhost:8000
2. Click "Admin" 
3. Click "AI Models" tab
4. Click on any agent card to edit

### Current Limitation
The UI currently edits Firestore records, but the copywriting service uses hardcoded personas. To connect them, you'd need to modify `get_agent_enhancements()` to fetch from Firestore instead.

## Detailed Editing Examples

### Example 1: Make Email Marketing Expert More Aggressive
```python
"email_marketing_expert": {
    "role": "aggressive sales-focused email specialist",
    "focus": "immediate conversions, hard-selling tactics, and urgency creation",
    "style": "Use strong CTAs, multiple urgency triggers, and scarcity. Be direct and pushy. Create FOMO at every opportunity.",
    "techniques": ["hard sell", "extreme urgency", "aggressive CTAs", "scarcity bombing"]
}
```

### Example 2: Make Compliance Officer More Relaxed
```python
"compliance_officer": {
    "role": "balanced legal advisor",
    "focus": "essential compliance without overwhelming the message",
    "style": "Include necessary disclaimers subtly. Keep legal language minimal and reader-friendly.",
    "techniques": ["soft disclaimers", "readable terms", "minimal legalese"]
}
```

### Example 3: Add a New Agent
```python
agent_personas = {
    # ... existing agents ...
    
    "luxury_brand_specialist": {  # New agent
        "role": "luxury brand copywriter specializing in premium markets",
        "focus": "exclusivity, prestige, and aspirational messaging",
        "style": "Elegant, sophisticated language. Focus on quality over price. Create desire through exclusivity.",
        "techniques": ["exclusivity messaging", "prestige positioning", "aspirational language", "quality emphasis"]
    }
}
```

## Advanced Customization

### Add Conditional Logic
You can also edit the conditional logic that applies based on agent combinations (lines 889-896):

```python
# Add new conditions based on your agents
if "luxury_brand_specialist" in agents:
    prompt += "\n\nIMPORTANT: Use elegant, sophisticated language. Never mention discounts directly."

if "email_marketing_expert" in agents and "compliance_officer" in agents:
    prompt += "\n\nBALANCE: Be persuasive but ensure all claims are legally compliant."
```

## Testing Your Changes

After editing, test that your changes work:

### Quick Test
```bash
# Test a specific agent
curl -X POST http://localhost:8002/api/generate-copy \
  -H "Content-Type: application/json" \
  -d '{
    "brief_content": "Test email for summer sale",
    "selected_agents": ["email_marketing_expert"],
    "selected_model": "gpt-3.5-turbo"
  }'
```

### Compare Different Agents
```bash
# Run the comparison test
python3 test_agent_quick.py
```

## Important Notes

### Current Architecture
- **Hardcoded in Backend**: Agent personas are currently defined directly in the Python code
- **Not Using Firestore**: The UI edits Firestore, but generation uses hardcoded values
- **Immediate Effect**: Changes to main.py take effect immediately (with --reload flag)

### To Make UI Edits Work
If you want the Admin UI to control agents, modify `get_agent_enhancements()`:

```python
async def get_agent_enhancements(agent_ids: List[str]) -> Dict[str, str]:
    """Get agent-specific prompt enhancements from Firestore"""
    
    # Fetch from Firestore instead of hardcoded
    db = get_firestore_client()
    enhancements = {}
    
    for agent_id in agent_ids:
        # Fetch from Firestore
        agent_doc = db.collection('agents').document(agent_id).get()
        if agent_doc.exists:
            agent_data = agent_doc.to_dict()
            enhancements[agent_id] = {
                "role": agent_data.get("role", "specialist"),
                "focus": agent_data.get("focus", "general copywriting"),
                "style": agent_data.get("style", "professional"),
                "techniques": agent_data.get("techniques", [])
            }
    
    return enhancements
```

## File Locations Summary

| What to Edit | File Location | Line Numbers |
|-------------|---------------|--------------|
| Agent Personas | `/copywriting/main.py` | Lines 808-851 |
| Agent Conditional Logic | `/copywriting/main.py` | Lines 889-896 |
| Agent Enhancement Application | `/copywriting/main.py` | Lines 874-886 |
| Admin UI (not connected) | `/frontend/public/components/AdminAgentsPanel.js` | - |

## Quick Edit Commands

```bash
# Open file in editor
code /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/copywriting/main.py

# Or with nano
nano +808 /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/copywriting/main.py

# Search for agent definitions in vim
vim /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/copywriting/main.py
# Then type: /agent_personas
```

That's how you edit the agent instructions! The quickest way is to directly modify the `agent_personas` dictionary in `main.py`.