# 📅 EmailPilot.ai Calendar Tab Integration

## 🎯 Overview
This package contains everything needed to integrate the Firebase calendar into your existing EmailPilot.ai Calendar tab.

## 🚀 Quick Integration Steps

### 1. Upload Backend Files
Upload these files to your EmailPilot.ai server:

**Note:** The deployment system will look for `deploy_to_emailpilot.sh` in your package and execute it automatically.

- `main.py` (replace existing - includes Firebase routes)
- `firebase_calendar_integration.py` (new file)
- `app/api/firebase_calendar.py` (new file)
- `service-account.json` (secure location)

### 2. Set Environment Variables
Add to your production environment:
```bash
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs
```

### 3. Update Calendar Tab Frontend
Replace your existing Calendar tab component with:
```javascript
import EmailPilotCalendarTab from './frontend/calendar/EmailPilotCalendarTab.js';

// In your main app routing
<Route path="/calendar" component={EmailPilotCalendarTab} />
```

### 4. Include Required Components
Copy these components to your frontend:
- `EmailPilotCalendarTab.js` (main component)
- `CalendarView.js` (calendar interface) 
- `CalendarChat.js` (AI assistant)
- `Calendar.js` (calendar logic)
- `EventModal.js` (event editing)

### 5. Test Integration
1. Restart your EmailPilot.ai application
2. Navigate to the Calendar tab
3. Select a client
4. Test calendar functionality

## ✅ Features Available in Calendar Tab

- **📅 Visual Calendar** - Drag & drop campaign planning
- **🤖 AI Assistant** - Gemini-powered campaign suggestions  
- **👥 Client Context** - Automatically uses selected client
- **📊 Statistics** - Campaign analytics and insights
- **📁 Import/Export** - Google Docs integration
- **🔄 Real-time Sync** - Instant updates across devices
- **📱 Responsive** - Works on desktop and mobile

## 🔐 Security Considerations

- Secure `service-account.json` with appropriate permissions
- Use environment variables for sensitive data
- Configure Firebase security rules
- Enable HTTPS in production

## 📊 Monitoring

Monitor your Calendar tab integration:
- Firebase Console: https://console.firebase.google.com/project/emailpilot-438321
- Application logs for API calls
- User engagement with calendar features

## 🆘 Support

If you encounter issues:
1. Check Firebase connection in console
2. Verify environment variables are set
3. Confirm client authentication works
4. Test API endpoints individually

Your Calendar tab will be enhanced with powerful Firebase-backed functionality!
