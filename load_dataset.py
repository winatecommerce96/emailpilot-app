#!/usr/bin/env python3
"""
Load and validate datasets for LangGraph Studio
"""
import json
import sys
from pathlib import Path
from typing import List, Dict, Any

def load_jsonl_dataset(file_path: str) -> List[Dict[str, Any]]:
    """Load a JSONL dataset file"""
    dataset = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                dataset.append(json.loads(line))
    return dataset

def validate_calendar_dataset(dataset: List[Dict[str, Any]]) -> bool:
    """Validate the calendar dataset format"""
    required_fields = ['input']
    valid = True
    
    for i, record in enumerate(dataset):
        # Check required fields
        for field in required_fields:
            if field not in record:
                print(f"❌ Record {i}: Missing required field '{field}'")
                valid = False
        
        # Check input structure
        if 'input' in record:
            input_data = record['input']
            if 'messages' not in input_data:
                print(f"⚠️ Record {i}: Input missing 'messages' field")
    
    return valid

def get_dataset(name: str = "emailpilot-calendar") -> List[Dict[str, Any]]:
    """Get a dataset by name for LangGraph Studio"""
    datasets_dir = Path(__file__).parent / "datasets"
    
    # Try different file formats
    for ext in ['.jsonl', '.json']:
        file_path = datasets_dir / f"{name}{ext}"
        if file_path.exists():
            print(f"✅ Loading dataset from: {file_path}")
            
            if ext == '.jsonl':
                dataset = load_jsonl_dataset(file_path)
            else:
                with open(file_path) as f:
                    dataset = json.load(f)
            
            # Validate
            if validate_calendar_dataset(dataset):
                print(f"✅ Dataset '{name}' validated successfully")
            else:
                print(f"⚠️ Dataset '{name}' has validation warnings")
            
            return dataset
    
    print(f"❌ Dataset '{name}' not found in {datasets_dir}")
    return []

def create_langgraph_dataset(dataset_name: str = "emailpilot-calendar") -> Dict[str, Any]:
    """Create a dataset in LangGraph Studio format"""
    dataset = get_dataset(dataset_name)
    
    if not dataset:
        return {}
    
    # Format for LangGraph Studio
    langgraph_dataset = {
        "name": dataset_name,
        "description": f"Test dataset for {dataset_name} workflow",
        "examples": dataset,
        "metadata": {
            "version": "1.0.0",
            "created_at": "2025-08-22",
            "num_examples": len(dataset)
        }
    }
    
    return langgraph_dataset

def main():
    """Main entry point for dataset loading"""
    print("\n" + "="*70)
    print("LANGGRAPH DATASET LOADER")
    print("="*70 + "\n")
    
    # Check available datasets
    datasets_dir = Path(__file__).parent / "datasets"
    datasets_dir.mkdir(exist_ok=True)
    
    print("📁 Available datasets:")
    for file in datasets_dir.glob("*.jsonl"):
        print(f"  • {file.stem}")
    print()
    
    # Load the emailpilot-calendar dataset
    dataset_name = "emailpilot-calendar"
    print(f"Loading '{dataset_name}' dataset...")
    
    dataset = get_dataset(dataset_name)
    
    if dataset:
        print(f"\n✅ Loaded {len(dataset)} examples")
        
        # Show sample
        print("\n📋 Sample record:")
        print(json.dumps(dataset[0], indent=2))
        
        # Create LangGraph format
        langgraph_data = create_langgraph_dataset(dataset_name)
        
        # Save in LangGraph format
        output_file = datasets_dir / f"{dataset_name}-langgraph.json"
        with open(output_file, 'w') as f:
            json.dump(langgraph_data, f, indent=2)
        
        print(f"\n✅ Saved LangGraph format to: {output_file}")
        
        # Instructions for LangGraph Studio
        print("\n" + "="*70)
        print("LANGGRAPH STUDIO INSTRUCTIONS")
        print("="*70)
        print(f"""
To use this dataset in LangGraph Studio:

1. The dataset is available at:
   ./datasets/{dataset_name}.jsonl

2. It's configured in langgraph.json:
   "datasets": {{
     "{dataset_name}": "./datasets/{dataset_name}.jsonl"
   }}

3. Access LangGraph Studio at:
   https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

4. The dataset will appear in the Studio's testing interface

5. You can run batch tests against the dataset
""")
    else:
        print("❌ Failed to load dataset")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())