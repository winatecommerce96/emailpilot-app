// Open browser console and run this to check the status

console.log("=== WORKFLOW INTEGRATION CHECK ===");

// 1. Check if workflow filter exists
const workflowFilter = document.getElementById('workflow-filter');
if (workflowFilter) {
    console.log("✅ Workflow filter found");
    console.log("   Options:", Array.from(workflowFilter.options).map(o => o.text));
    console.log("   Current value:", workflowFilter.value);
} else {
    console.log("❌ Workflow filter NOT found");
}

// 2. Check if workflow indicator exists
const workflowIndicator = document.getElementById('workflow-indicator');
if (workflowIndicator) {
    console.log("✅ Workflow indicator found");
    console.log("   Hidden:", workflowIndicator.classList.contains('hidden'));
} else {
    console.log("❌ Workflow indicator NOT found");
}

// 3. Check if agents dropdown exists
const agentsSelect = document.getElementById('existing-agents-select');
if (agentsSelect) {
    console.log("✅ Agents dropdown found");
    console.log("   Options count:", agentsSelect.options.length);
    
    // Check for workflow badges
    const optionsWithBadges = Array.from(agentsSelect.options).filter(o => 
        o.text.includes('[') && o.text.includes(']')
    );
    console.log("   Options with badges:", optionsWithBadges.length);
    if (optionsWithBadges.length > 0) {
        console.log("   Sample badges:", optionsWithBadges.slice(0, 3).map(o => o.text));
    }
    
    // Check for color coding
    const coloredOptions = Array.from(agentsSelect.options).filter(o => 
        o.style.backgroundColor !== ''
    );
    console.log("   Options with color:", coloredOptions.length);
} else {
    console.log("❌ Agents dropdown NOT found");
}

// 4. Check global variables
console.log("=== GLOBAL VARIABLES ===");
console.log("workflowAgents:", typeof workflowAgents, Object.keys(workflowAgents || {}).length);
console.log("allAgentsList:", typeof allAgentsList, Array.isArray(allAgentsList) ? allAgentsList.length : 0);

console.log("=== END CHECK ===");
