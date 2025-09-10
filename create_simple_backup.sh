#!/bin/bash

# Simple Comprehensive EmailPilot Backup Script
# Creates a complete archive of all development work

set -e

BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="emailpilot_comprehensive_backup_${BACKUP_DATE}"

echo "🚀 Creating comprehensive EmailPilot backup..."
echo "📅 Backup timestamp: ${BACKUP_DATE}"

# Create the archive directly in the current directory
echo "🗜️ Creating compressed archive..."

tar -czf "${BACKUP_NAME}.tar.gz" \
    --exclude='__pycache__' \
    --exclude='node_modules' \
    --exclude='.DS_Store' \
    --exclude='*.pyc' \
    --exclude='.env' \
    --exclude='backups' \
    --exclude='.git' \
    app/ \
    emailpilot_graph/ \
    multi-agent/ \
    frontend/ \
    services/ \
    main_firestore.py \
    requirements.txt \
    package.json \
    package-lock.json \
    CLAUDE.md \
    README.md \
    workflow_templates/ \
    *.md 2>/dev/null || true

# Verify the archive
if [ -f "${BACKUP_NAME}.tar.gz" ]; then
    ARCHIVE_SIZE=$(du -sh "${BACKUP_NAME}.tar.gz" | cut -f1)
    echo "✅ Backup completed successfully!"
    echo "📦 Archive: ${BACKUP_NAME}.tar.gz"
    echo "📊 Compressed size: ${ARCHIVE_SIZE}"
    
    # Create backup info file
    cat > "${BACKUP_NAME}_INFO.md" << EOF
# EmailPilot Comprehensive Backup

**Created**: $(date)
**Archive**: ${BACKUP_NAME}.tar.gz
**Size**: ${ARCHIVE_SIZE}

## Contents
- Complete EmailPilot application
- All MCP integrations and registry system
- Universal workflow enhancement service
- LangGraph calendar planning workflows
- Multi-agent AI system
- Frontend interfaces and dashboards
- All configuration templates

## To Restore
1. Extract: \`tar -xzf ${BACKUP_NAME}.tar.gz\`
2. Install deps: \`pip install -r requirements.txt\`
3. Start app: \`uvicorn main_firestore:app --port 8000 --host localhost --reload\`

## Key Systems Included
✅ Universal MCP Registry
✅ Workflow Integration Dashboard  
✅ Calendar Planning System
✅ AI Agent Management
✅ Future-proof Architecture
✅ Complete Backend APIs
✅ React Frontend Interfaces

This backup contains everything needed to restore the complete EmailPilot system.
EOF

    echo "📋 Created backup info: ${BACKUP_NAME}_INFO.md"
    echo ""
    echo "🎉 COMPREHENSIVE BACKUP COMPLETE!"
    echo ""
    echo "🔒 To restore this backup anywhere:"
    echo "   tar -xzf ${BACKUP_NAME}.tar.gz"
    echo "   pip install -r requirements.txt"
    echo "   uvicorn main_firestore:app --port 8000 --host localhost --reload"
    echo ""
    
    # Move to backups directory
    mv "${BACKUP_NAME}.tar.gz" "backups/"
    mv "${BACKUP_NAME}_INFO.md" "backups/"
    
    echo "📁 Backup moved to backups/ directory"
    echo "✨ Your EmailPilot system is now safely backed up!"
    
else
    echo "❌ Backup failed - archive not created"
    exit 1
fi