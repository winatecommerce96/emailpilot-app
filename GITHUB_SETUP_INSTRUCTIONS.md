# GitHub Repository Setup Instructions

## Steps to Create and Push the EmailPilot LangGraph Repository

### 1. Authenticate with GitHub CLI

First, authenticate with GitHub:

```bash
gh auth login
```

Choose:
- GitHub.com
- HTTPS
- Login with a web browser (or use an authentication token)
- Follow the prompts to complete authentication

### 2. Create the Private Repository

Once authenticated, create a new private repository:

```bash
# Create private repository
gh repo create emailpilot-langgraph --private --description "EmailPilot LangGraph Integration - AI-powered campaign planning with visual workflows"
```

### 3. Add the Remote and Push

The repository already exists locally with uncommitted changes. Here's how to push it:

```bash
# Navigate to the project directory
cd /Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app

# Add all the new files (be selective if needed)
git add LANGGRAPH_README.md
git add LANGGRAPH_INTEGRATION.md
git add LANGGRAPH_MIGRATION.md
git add LANGGRAPH_TROUBLESHOOTING.md
git add LANGGRAPH_WORKFLOW_SYSTEM.md
git add CALENDAR_PLANNING_AI.md
git add CALENDAR_PLANNER_TECHNICAL_GUIDE.md
git add emailpilot_graph/
git add README.md
git add README_LANGGRAPH.md

# You may also want to add other important files:
git add app/api/hub.py
git add app/api/calendar_planning_ai.py
git add multi-agent/
git add requirements.txt
git add requirements.langgraph.txt

# Commit the changes
git commit -m "Initial commit: EmailPilot LangGraph integration with visual workflow orchestration"

# Add the remote (replace 'yourusername' with your GitHub username)
git remote add origin https://github.com/yourusername/emailpilot-langgraph.git

# Push to the main branch (or create a new branch)
git push -u origin feature/langgraph-studio-boot
```

### 4. Alternative: Push Everything (Including Uncommitted Changes)

If you want to push ALL the current state including uncommitted changes:

```bash
# Stage all changes (be careful with this)
git add -A

# Commit everything
git commit -m "Complete EmailPilot platform with LangGraph integration"

# Push to GitHub
git push -u origin feature/langgraph-studio-boot
```

### 5. Create Main Branch and Set as Default

After pushing, you might want to create a main branch:

```bash
# Create and switch to main branch
git checkout -b main

# Push main branch
git push -u origin main

# Set main as default branch on GitHub
gh repo edit emailpilot-langgraph --default-branch main
```

### 6. Add Repository Topics (Optional)

Add relevant topics to help with discoverability:

```bash
gh repo edit emailpilot-langgraph --add-topic "langgraph" --add-topic "langchain" --add-topic "klaviyo" --add-topic "email-marketing" --add-topic "ai-orchestration" --add-topic "fastapi"
```

### 7. Configure Repository Settings

Set up branch protection and other settings:

```bash
# Protect main branch (optional)
gh api repos/:owner/emailpilot-langgraph/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":[]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

## Important Notes

1. **Sensitive Files**: Make sure `.env` files and any files with API keys are in `.gitignore`
2. **Large Files**: Check for any large files that shouldn't be committed
3. **Private Repository**: The repository is created as private by default
4. **Branch Strategy**: Currently on `feature/langgraph-studio-boot` branch

## Verification

After pushing, verify the repository:

```bash
# Check repository info
gh repo view emailpilot-langgraph --web

# List files in repository
gh repo clone emailpilot-langgraph temp-check
ls -la temp-check/
rm -rf temp-check
```

## Repository URL

Once created, your repository will be available at:
```
https://github.com/[your-username]/emailpilot-langgraph
```

## Troubleshooting

If you encounter issues:

1. **Authentication Issues**: 
   ```bash
   gh auth refresh
   ```

2. **Remote Already Exists**:
   ```bash
   git remote remove origin
   git remote add origin https://github.com/yourusername/emailpilot-langgraph.git
   ```

3. **Large Files Issue**:
   ```bash
   # Find large files
   find . -type f -size +100M
   
   # Add to .gitignore if needed
   echo "large-file-name" >> .gitignore
   ```

---

Remember to replace `yourusername` with your actual GitHub username in all commands!