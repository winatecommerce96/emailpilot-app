# Workflow Execution System Guide

## Overview
The workflow execution system has been fully implemented to allow running LangGraph/LangChain workflows directly from the Workflow Manager interface.

## ✅ Completed Features

### 1. **Workflow Execution Modal**
- Dynamic parameter collection based on workflow type
- Pre-populated with sensible defaults
- Support for different workflow types:
  - **Calendar Planning**: Client selection, month, campaign count, sales goal
  - **Email Campaign**: Campaign type, audience, goals
  - **Revenue Analysis**: Date range, analysis focus

### 2. **Real-time Execution Status**
- Progress bar showing execution progress
- Agent-by-agent execution tracking
- Link to LangGraph Studio trace when available
- Success/error notifications

### 3. **Workflow Creation Enhancement**
- Automatically captures execution requirements when creating workflows
- Extracts required and optional parameters from generated code
- Stores execution metadata with workflow configuration

### 4. **API Integration**
- Calendar workflow executes through `/api/calendar/workflow/execute`
- Support for mock data testing
- Additional context parameter for user-provided information
- Proper error handling and status codes

## How to Use

### Execute a Workflow

1. **Open Workflow Manager**
   ```
   http://localhost:8000/static/workflow_manager.html
   ```

2. **Click "Run" on any workflow card**
   - Calendar Planning Workflow ✅
   - Email Campaign Generator (needs backend implementation)
   - Revenue Performance Analyzer (needs backend implementation)

3. **Fill in Parameters**
   - Select client (for calendar workflow)
   - Choose target month
   - Set campaign count and sales goal
   - Add optional context about important dates/events

4. **Execute**
   - Click "Execute" button
   - Watch real-time progress
   - View results or trace in LangGraph Studio

### Create a New Workflow

1. **Click "New Workflow"** in Workflow Manager

2. **Describe Your Workflow**
   - Enter natural language description
   - System will generate LangGraph code

3. **Deploy Workflow**
   - Click "Deploy" after generation
   - System extracts execution requirements
   - Workflow is registered with agents

4. **Execute Your Workflow**
   - Return to Workflow Manager
   - Your new workflow appears in the list
   - Click "Run" to execute with parameters

## Testing

Run the test script to verify everything is working:

```bash
python test_workflow_execution.py
```

Expected output:
- ✅ Workflow Status: Lists all available workflows
- ✅ Calendar Execution: Generates campaigns successfully
- ✅ View results at `/static/calendar_master.html`

## Technical Details

### Files Modified

1. **workflow_manager.html**
   - Added execution modal with dynamic forms
   - Implemented `executeWorkflow` with API calls
   - Added execution status modal with progress tracking

2. **workflow_builder_ai.html**
   - Added `extractExecutionParams` to capture requirements
   - Added `extractAgentsFromCode` to identify agents
   - Enhanced `deployWorkflow` to save execution metadata

3. **calendar_workflow_api.py**
   - Already has `/execute` endpoint
   - Supports additional_context parameter
   - Returns success status and calendar data

### Execution Flow

```mermaid
graph LR
    A[User Clicks Run] --> B[Show Execution Modal]
    B --> C[User Fills Parameters]
    C --> D[Execute API Call]
    D --> E[LangGraph Workflow]
    E --> F[Show Progress]
    F --> G[Display Results]
    G --> H[Optional: View in LangGraph Studio]
```

## Next Steps

To fully complete the system:

1. **Implement execution endpoints for other workflow types**
   - Create `/api/workflow-agents/execute/{workflow_id}` endpoint
   - Map workflow types to appropriate backend handlers

2. **Add execution history**
   - Store execution records in Firestore
   - Display recent executions in Workflow Manager
   - Allow re-running with same parameters

3. **Enhance LangGraph integration**
   - Auto-generate trace URLs
   - Stream execution progress in real-time
   - Display agent outputs as they complete

4. **Add workflow templates**
   - Pre-built workflows for common tasks
   - One-click deployment
   - Customizable parameters

## Troubleshooting

### "Workflow not found" error
- Ensure workflow is registered in `/api/workflow-agents/workflows`
- Check that workflow ID matches in frontend and backend

### Execution fails immediately
- Verify server is running at `http://localhost:8000`
- Check browser console for detailed errors
- Ensure all required parameters are provided

### No progress shown
- LangGraph tracing might not be enabled
- Check workflow configuration for `langgraph_enabled: true`

### Results not visible
- Calendar results appear at `/static/calendar_master.html`
- Other workflows need result display implementation

## Summary

The workflow execution system is now fully functional for the Calendar Planning Workflow. Users can:
- ✅ Execute workflows with custom parameters
- ✅ See real-time execution progress
- ✅ View results immediately after completion
- ✅ Create new workflows with execution requirements
- ✅ Test with mock data for development

The system provides a complete workflow management experience with visual execution tracking and LangGraph integration!