#!/bin/bash

# Archive Old Calendar Implementations Script
# This script moves old calendar implementations to an archive folder to prevent conflicts

ARCHIVE_DIR="archived_old_calendars_$(date +%Y%m%d_%H%M%S)"
CURRENT_DIR=$(pwd)

echo "🗄️  Archiving old calendar implementations..."
echo "Archive directory: $ARCHIVE_DIR"

# Create archive directory
mkdir -p "$ARCHIVE_DIR"

# List of old calendar directories to archive
OLD_CALENDAR_DIRS=(
    "calendar-project"
    "calendar-implementation-complete"
    "calendar-implementation-complete 2"
    "emailpilot_calendar_tab_20250809_122906"
    "emailpilot_calendar_tab_20250809_122906 2"
    "emailpilot_firebase_deploy_20250809_122212"
    "calendar-goals-package"
    "calendar-api-fix"
    "calendar-react-feature"
    "emailpilot-calendar-spa-deployment"
    "emailpilot-calendar-spa-fixed"
)

# Archive each directory if it exists
for dir in "${OLD_CALENDAR_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  📦 Archiving: $dir"
        mv "$dir" "$ARCHIVE_DIR/"
    fi
done

# Archive old calendar HTML files (keep only the working ones)
OLD_CALENDAR_FILES=(
    "calendar_fixed.html"
    "calendar_integrated.html"
    "calendar_production.html"
)

for file in "${OLD_CALENDAR_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  📄 Archiving: $file"
        mv "$file" "$ARCHIVE_DIR/"
    fi
done

# Archive old calendar-related ZIP files
if ls *.zip 1> /dev/null 2>&1; then
    echo "  🗜️  Archiving ZIP files..."
    mkdir -p "$ARCHIVE_DIR/zip_files"
    mv *calendar*.zip "$ARCHIVE_DIR/zip_files/" 2>/dev/null || true
fi

# Create a manifest of what was archived
echo "📝 Creating archive manifest..."
cat > "$ARCHIVE_DIR/ARCHIVE_MANIFEST.md" << EOF
# Archived Calendar Implementations
Date: $(date)
Reason: Preventing conflicts with main EmailPilot calendar integration

## Archived Directories:
$(ls -la "$ARCHIVE_DIR" 2>/dev/null | grep "^d" | awk '{print "- " $NF}')

## Archived Files:
$(ls -la "$ARCHIVE_DIR" 2>/dev/null | grep "^-" | awk '{print "- " $NF}')

## Current Working Implementation:
- Main file: main_firestore.py
- Frontend: frontend/public/
- API: app/api/

## To restore any archived item:
mv archived_old_calendars_*/[item_name] .
EOF

echo "✅ Archive complete! Old calendar implementations moved to: $ARCHIVE_DIR"
echo ""
echo "📍 Current working implementation remains in:"
echo "   - main_firestore.py (main application)"
echo "   - frontend/public/ (React components)"
echo "   - app/api/ (API endpoints)"
echo ""
echo "💡 To restore any archived item, check: $ARCHIVE_DIR/ARCHIVE_MANIFEST.md"