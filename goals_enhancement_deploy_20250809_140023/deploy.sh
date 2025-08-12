#\!/bin/bash
echo "🎯 Deploying Goals Enhancement..."
cp -r app/* /path/to/emailpilot/app/
cp -r frontend/* /path/to/emailpilot/frontend/
cp firebase_goals_calendar_integration.py /path/to/emailpilot/
echo "✅ Files copied. Remember to update main.py and restart\!"
