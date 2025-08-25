# Calendar Creation & Prompt Tuning Guide

## 🎯 Quick Start: Where to Do What

### For Different Tasks:

| Task | Best Tool | Why |
|------|-----------|-----|
| **Create Calendar** | LangGraph Studio | Visual workflow, see data flow |
| **Tune Prompts** | Admin Dashboard | Live editing, instant save |
| **Test Changes** | Python Script | Quick iteration, detailed logs |
| **Production Use** | API Endpoint | Integrated with app |

---

## Option 1: LangGraph Studio (Visual & Interactive) 🎨

**Best for: Creating calendars, seeing data flow, debugging**

### Access:
1. Open: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
2. Select "live_calendar" graph

### Create a Calendar:
```json
// Input this in the Studio interface:
{
  "client_id": "test-client-001",
  "month": "2025-03",
  "timestamp": "2025-08-23T12:00:00",
  "errors": [],
  "status": "started"
}
```

### What You'll See:
- Each node lighting up as it executes
- Data flowing between nodes
- Real-time results in each step
- Final calendar output

---

## Option 2: Admin Dashboard (Prompt Editing) ✏️

**Best for: Tuning agent prompts, managing AI behavior**

### Access:
```bash
# Make sure server is running
uvicorn main_firestore:app --port 8000 --host localhost --reload
```

Then open: http://localhost:8000/static/dist/index.html

### Navigate to Agent Prompts:
1. Click "Admin" in navigation
2. Select "Agent Prompts" tab
3. Edit prompts for:
   - `campaign_planner` - Main calendar creation
   - `copy_smith` - Email copywriting
   - `revenue_analyst` - Revenue projections
   - `audience_architect` - Segmentation

### Edit Prompts Live:
```javascript
// Example: Customize campaign_planner prompt
You are a Campaign Planning Expert for {brand} in {month}.
Create a comprehensive email campaign strategy including:
- 4 emails per week (Mon, Wed, Fri, Sat)
- Focus on {industry} best practices
- Target these segments: {segments}
- Include seasonal themes for {month}
Format as JSON with dates, subjects, and segments.
```

---

## Option 3: Python Script (Fast Testing) 🐍

**Best for: Quick iterations, debugging, batch processing**

### Create Test Script:
```python
#!/usr/bin/env python3
# save as: create_my_calendar.py

from graph.live_graph import create_live_calendar_graph
from datetime import datetime
import json

# Create the graph
app = create_live_calendar_graph()

# Your client configuration
MY_CLIENT = {
    'client_id': 'fashionbrand-001',  # Change to your client
    'month': '2025-03',               # Target month
    'timestamp': datetime.now().isoformat(),
    'errors': [],
    'status': 'started'
}

# Run the calendar creation
print("🚀 Creating calendar...")
result = app.invoke(MY_CLIENT)

# Save results
with open(f"calendar_{MY_CLIENT['client_id']}_{MY_CLIENT['month']}.json", "w") as f:
    json.dump(result, f, indent=2)

# Display key results
print(f"✅ Status: {result.get('status')}")
print(f"📅 Campaigns: {len(result.get('campaign_plan', {}).get('campaigns', []))}")
print(f"📧 Templates: {len(result.get('email_templates', []))}")

# Show the actual calendar
if result.get('campaign_plan'):
    print("\n📅 CALENDAR PREVIEW:")
    for campaign in result['campaign_plan']['campaigns'][:5]:
        print(f"  {campaign.get('date')} - {campaign.get('subject')}")
```

### Run it:
```bash
python create_my_calendar.py
```

---

## Option 4: HTML Dashboard (User-Friendly) 🌐

**Best for: Non-technical users, quick access**

### Access Calendar Tools:
Open: http://localhost:8000/static/dist/calendar_tools.html

### Features:
- Quick workflow runner
- System status display
- Direct calendar creation
- Results visualization

---

## Option 5: Integrated System (Full Control) 🔧

**Best for: Complete control, all features**

### Use the Integrated System:
```python
from integrated_calendar_system import IntegratedCalendarSystem

system = IntegratedCalendarSystem()

# 1. Edit a prompt
system.edit_agent_prompt(
    "campaign_planner",
    """Create a high-converting email campaign calendar for {brand}.
    Focus on {month} seasonal trends and holidays.
    Include: dates, subjects, segments, expected metrics.
    Optimize for mobile-first readers."""
)

# 2. Run complete workflow
results = system.run_complete_workflow(
    brand="YourBrand",
    month="March 2025",
    goals=["Spring sale", "New collection launch", "Re-engage dormant"]
)

# 3. Results include everything
print(results['campaign_plan'])
print(results['email_templates'])
print(results['send_schedule'])
```

---

## 📝 Prompt Tuning Workflow

### Step 1: Start with Base Prompt
```python
# In admin dashboard or via code
base_prompt = """
You are a Campaign Planning Expert for {brand} in {month}.
Create email campaigns based on industry best practices.
"""
```

### Step 2: Test with Real Data
```python
# Run with your client
result = app.invoke({
    'client_id': 'your-real-client',
    'month': '2025-03'
})
```

### Step 3: Refine Based on Output
```python
# Too generic? Add specifics:
improved_prompt = """
You are a Campaign Planning Expert for {brand} in {month}.
Industry: {industry}
Available segments: {segments}
Past performance: {metrics}

Create 12 email campaigns with:
- Specific dates (avoid Mondays)
- Compelling subject lines (40-60 chars)
- Target segment for each
- Expected open rate based on past data
- A/B test variants for top 3 campaigns

Format as JSON with this structure:
{
  "campaigns": [
    {
      "date": "2025-03-05",
      "subject": "Spring Collection Launch 🌸",
      "segment": "vip_customers",
      "expected_open_rate": 0.28,
      "type": "promotional"
    }
  ]
}
"""
```

### Step 4: Save and Test
```python
# Save improved prompt
system.edit_agent_prompt("campaign_planner", improved_prompt)

# Test again
new_result = system.run_complete_workflow(...)
```

---

## 🔄 Recommended Development Flow

### 1. **Initial Setup** (5 min)
```bash
# Terminal 1: Start main server
uvicorn main_firestore:app --port 8000 --host localhost --reload

# Terminal 2: Start LangGraph Studio
langgraph dev --port 2024

# Terminal 3: Start MCP if needed
./start_mcp_servers.sh
```

### 2. **First Calendar** (2 min)
- Open LangGraph Studio
- Input client_id and month
- Watch it run
- Review output

### 3. **Tune Prompts** (10 min)
- Open Admin Dashboard
- Go to Agent Prompts
- Edit campaign_planner prompt
- Add your specific requirements

### 4. **Test Changes** (2 min)
- Run Python script with same client
- Compare outputs
- Iterate on prompts

### 5. **Production Ready** (5 min)
- Save final prompts
- Test with multiple clients
- Deploy

---

## 🎯 Pro Tips

### For Better Calendars:
1. **Add Industry Context**: Include industry in prompts
2. **Use Past Data**: Reference historical performance
3. **Segment Wisely**: Target specific audience segments
4. **Test Timing**: Optimize send days/times
5. **Include Holidays**: Reference month-specific events

### For Prompt Tuning:
1. **Start Simple**: Basic prompt first, then add complexity
2. **Use Examples**: Show the AI what you want
3. **Be Specific**: Exact requirements get better results
4. **Test Iteratively**: Small changes, test, repeat
5. **Save Versions**: Keep track of what works

### For Debugging:
1. **Check Logs**: Look at terminal output
2. **Use LangGraph Studio**: Visual debugging
3. **Inspect State**: Print intermediate results
4. **Test Nodes Individually**: Isolate issues

---

## 📊 Example: Complete Calendar Creation

### Input (minimal):
```json
{
  "client_id": "fashionbrand-001",
  "month": "2025-03"
}
```

### Output (comprehensive):
```json
{
  "campaign_plan": {
    "brand": "FashionBrand",
    "month": "2025-03",
    "campaigns": [
      {
        "date": "2025-03-05",
        "subject": "Spring Collection Launch 🌸",
        "segment": "all_subscribers",
        "type": "announcement",
        "expected_open_rate": 0.25
      },
      {
        "date": "2025-03-08",
        "subject": "International Women's Day Sale",
        "segment": "female_customers",
        "type": "promotional",
        "expected_open_rate": 0.30
      }
      // ... more campaigns
    ]
  },
  "email_templates": [...],
  "send_schedule": {
    "best_times": {...},
    "frequency_cap": 3
  }
}
```

---

## 🚀 Start Now!

1. **Quickest Start**: Open LangGraph Studio and input a client_id
2. **Most Control**: Use Python script
3. **Best for Prompts**: Admin Dashboard
4. **Most Visual**: LangGraph Studio

The system is ready - just pick your preferred interface and start creating calendars!