# LangGraph Studio Datasets

This directory contains test datasets for the EmailPilot Calendar workflow in LangGraph Studio.

## Available Datasets

### 1. emailpilot-calendar.jsonl
Main dataset with 10 test cases for different brands and campaign scenarios.

**Format:**
```jsonl
{
  "input": {
    "messages": [{"role": "user", "content": "..."}]
  },
  "expected": {
    "brand": "...",
    "month": "...",
    "goals": [...],
    "campaign_count": N
  }
}
```

### 2. calendar-test-cases.jsonl
Extended test cases with thread IDs and configuration for stateful testing.

**Format:**
```jsonl
{
  "thread_id": "test-001",
  "input": {
    "brand": "...",
    "month": "...",
    "messages": [...]
  },
  "config": {
    "configurable": {"thread_id": "test-001"}
  }
}
```

## Using Datasets in LangGraph Studio

### Method 1: Automatic Loading
The datasets are configured in `langgraph.json`:
```json
{
  "datasets": {
    "emailpilot-calendar": "./datasets/emailpilot-calendar.jsonl"
  }
}
```

When you open LangGraph Studio, the dataset will be available in the testing interface.

### Method 2: Manual Import
1. Open LangGraph Studio: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
2. Navigate to the Testing tab
3. Click "Import Dataset"
4. Select the JSONL file from this directory

### Method 3: Programmatic Testing
```python
from load_dataset import get_dataset, create_langgraph_dataset

# Load dataset
dataset = get_dataset("emailpilot-calendar")

# Use in tests
for test_case in dataset:
    result = calendar_graph.invoke(test_case["input"])
    # Compare with test_case["expected"]
```

## Running Batch Tests

1. **In LangGraph Studio:**
   - Select the dataset from the dropdown
   - Click "Run All Tests"
   - View results in the test results panel

2. **From Command Line:**
   ```bash
   python load_dataset.py  # Validate datasets
   python run_batch_tests.py  # Run all test cases
   ```

## Adding New Test Cases

To add new test cases, append to the JSONL file:

```bash
echo '{"input": {"messages": [{"role": "user", "content": "New test"}]}, "expected": {...}}' >> emailpilot-calendar.jsonl
```

Or use the Python helper:
```python
import json

new_test = {
    "input": {
        "messages": [
            {"role": "user", "content": "Your test prompt"}
        ]
    },
    "expected": {
        "brand": "TestBrand",
        "month": "Month Year",
        "goals": ["Goal 1", "Goal 2"],
        "campaign_count": 10
    }
}

with open("datasets/emailpilot-calendar.jsonl", "a") as f:
    f.write(json.dumps(new_test) + "\n")
```

## Test Coverage

Current test cases cover:
- **Seasonal Campaigns**: Spring, Summer, Fall, Winter
- **Holiday Campaigns**: Valentine's Day, Mother's Day, Black Friday, Christmas
- **Product Launches**: New collections, feature releases
- **Re-engagement**: Win-back campaigns, loyalty programs
- **Industries**: Fashion, Tech, Beauty, Fitness, Pet, Books, Food, Travel, Home, Sports

## Validation

Run validation to ensure dataset integrity:
```bash
python load_dataset.py
```

This will:
- Check JSONL format
- Validate required fields
- Display statistics
- Generate LangGraph-compatible format