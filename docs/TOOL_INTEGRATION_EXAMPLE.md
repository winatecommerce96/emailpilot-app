# Tool Integration Example - How to Add UI Features Programmatically

## For AI Agents and Automation Tools

This document shows how tools can programmatically add UI features to EmailPilot by reading the documentation.

### 1. Read the UI Manifest

```python
import json

# Load the UI system specification
with open('ui-manifest.json', 'r') as f:
    ui_spec = json.load(f)

# Get the required steps
steps = ui_spec['required_steps_for_new_ui']
for step in steps:
    print(f"Step {step['step']}: {step['action']}")
    print(f"  Location: {step['location']}")
    print(f"  Example: {step.get('example', 'N/A')}")
```

### 2. Generate Component Code

```python
def create_ui_component(name, content):
    """Generate a React component for EmailPilot"""
    
    template = f"""
// Auto-generated component
const {name} = () => {{
    const [data, setData] = React.useState(null);
    const [loading, setLoading] = React.useState(false);
    
    React.useEffect(() => {{
        // Fetch data from backend
        fetch('/api/{name.lower()}')
            .then(res => res.json())
            .then(setData)
            .catch(console.error);
    }}, []);
    
    return React.createElement('div', {{ className: 'p-6 bg-white rounded-lg shadow' }},
        React.createElement('h2', {{ className: 'text-2xl font-bold mb-4' }}, '{name}'),
        React.createElement('div', null, '{content}'),
        loading && React.createElement('div', null, 'Loading...'),
        data && React.createElement('pre', null, JSON.stringify(data, null, 2))
    );
}};

// CRITICAL: Export to window for EmailPilot
window.{name} = {name};
"""
    
    # Save component
    with open(f'frontend/public/components/{name}.js', 'w') as f:
        f.write(template)
    
    return f"Component {name} created"
```

### 3. Update Build Configuration

```python
def add_to_build_system(component_name):
    """Add component to build script"""
    
    build_script = 'scripts/build_frontend.sh'
    
    # Read current script
    with open(build_script, 'r') as f:
        content = f.read()
    
    # Find JSX_COMPONENTS array
    import re
    pattern = r'(JSX_COMPONENTS=\([^)]+)'
    
    def replacer(match):
        current = match.group(1)
        # Add new component if not already present
        if component_name not in current:
            return current + f'\n    "{component_name}"'
        return current
    
    # Update script
    new_content = re.sub(pattern, replacer, content)
    
    with open(build_script, 'w') as f:
        f.write(new_content)
    
    return f"Added {component_name} to build system"
```

### 4. Add Script Include

```python
def add_to_html(component_name):
    """Add script tag to HTML"""
    
    html_file = 'frontend/public/index.html'
    script_tag = f'    <script src="/static/dist/{component_name}.js"></script>\n'
    
    with open(html_file, 'r') as f:
        lines = f.readlines()
    
    # Find where to insert (around line 472)
    insert_index = None
    for i, line in enumerate(lines):
        if 'DeveloperTools.js' in line:
            insert_index = i + 1
            break
    
    if insert_index:
        lines.insert(insert_index, script_tag)
        
        with open(html_file, 'w') as f:
            f.writelines(lines)
        
        return f"Added {component_name} script to HTML"
    
    return "Could not find insertion point"
```

### 5. Add to Quick Actions

```python
def add_quick_action(component_name, icon='🎯', subtitle='New feature'):
    """Add component to Quick Actions menu"""
    
    framework_file = 'frontend/public/components/QuickActionsFramework.js'
    
    new_action = f"""
    {{
      id: '{component_name.lower()}',
      icon: '{icon}',
      title: '{component_name}',
      subtitle: '{subtitle}',
      onClick: () => setActiveTab('{component_name.lower()}'),
      enabled: true,
      requiresComponent: true,
      componentName: '{component_name}',
      componentPath: '/static/dist/{component_name}.js'
    }},"""
    
    with open(framework_file, 'r') as f:
        content = f.read()
    
    # Insert before the last item in QUICK_ACTIONS_CONFIG
    import re
    pattern = r'(const QUICK_ACTIONS_CONFIG = \[[^]]+)(];)'
    
    def replacer(match):
        config = match.group(1)
        closing = match.group(2)
        # Add new action before closing
        return config + new_action + '\n  ' + closing
    
    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    
    with open(framework_file, 'w') as f:
        f.write(new_content)
    
    return f"Added {component_name} to Quick Actions"
```

### 6. Complete Automation Script

```python
#!/usr/bin/env python3
"""
Automated UI Feature Addition for EmailPilot
Usage: python add_ui_feature.py MyFeature "Feature description"
"""

import sys
import subprocess
import json

def add_ui_feature(name, description):
    """Completely automate adding a UI feature"""
    
    print(f"Adding UI feature: {name}")
    
    # Step 1: Create component
    print("1. Creating component...")
    create_ui_component(name, description)
    
    # Step 2: Add to build
    print("2. Adding to build system...")
    add_to_build_system(name)
    
    # Step 3: Add to HTML
    print("3. Adding script include...")
    add_to_html(name)
    
    # Step 4: Add to Quick Actions
    print("4. Adding to Quick Actions...")
    add_quick_action(name, '🚀', description)
    
    # Step 5: Build
    print("5. Building frontend...")
    subprocess.run(['npm', 'run', 'build'], check=True)
    
    # Step 6: Verify
    print("6. Verifying...")
    import os
    if os.path.exists(f'frontend/public/dist/{name}.js'):
        print(f"✅ Success! {name} has been added to the UI")
        print(f"   Access it via Quick Actions in /admin")
    else:
        print(f"❌ Build may have failed. Check manually.")
    
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python add_ui_feature.py ComponentName 'Description'")
        sys.exit(1)
    
    name = sys.argv[1]
    description = sys.argv[2]
    
    add_ui_feature(name, description)
```

## For LLM/AI Integration

When an AI model needs to add UI features, it should:

1. **Read the manifest**: Parse `ui-manifest.json` for system structure
2. **Follow the steps**: Execute each required step in order
3. **Use the patterns**: Copy from existing components in `existing_components`
4. **Verify success**: Check that files exist after build
5. **Test the UI**: Confirm component appears in Quick Actions

## Example AI Prompt

```
To add a new UI feature to EmailPilot:

1. Read ui-manifest.json to understand the system
2. Create component in frontend/public/components/NewFeature.js
3. Export it: window.NewFeature = NewFeature
4. Add "NewFeature" to JSX_COMPONENTS in scripts/build_frontend.sh
5. Add <script src="/static/dist/NewFeature.js"></script> to index.html
6. Run: npm run build
7. Verify: ls -la frontend/public/dist/NewFeature.js

The feature will appear in Quick Actions if you also update QuickActionsFramework.js
```

## Validation Checklist

After adding a UI feature programmatically:

- [ ] Component file exists: `frontend/public/components/{Name}.js`
- [ ] Window export present: `window.{Name} = {Name}`
- [ ] In build script: `grep {Name} scripts/build_frontend.sh`
- [ ] In HTML: `grep {Name}.js frontend/public/index.html`
- [ ] Built file exists: `ls frontend/public/dist/{Name}.js`
- [ ] No console errors when loading
- [ ] Appears in Quick Actions (if added)
- [ ] Clicking it works

## Success Metrics

A successfully integrated UI feature will:
1. Load without errors
2. Appear in the designated location
3. Connect to its backend endpoint
4. Handle loading and error states
5. Be accessible via Developer Tools

## Troubleshooting

If automated addition fails:
1. Check syntax in generated component
2. Verify build script syntax after modification
3. Ensure HTML script tag is properly formatted
4. Run `npm run build` manually and check for errors
5. Use `python diagnose_frontend_gaps.py` for analysis