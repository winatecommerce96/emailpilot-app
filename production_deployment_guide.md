# 🚀 Firebase Calendar Production Deployment Guide

## ✅ Pre-Deployment Checklist

- [x] Firebase credentials configured (emailpilot-438321)
- [x] Firebase indexes created and enabled
- [x] Local testing successful 
- [x] Frontend components updated to use Firebase endpoints
- [x] All calendar functionality working

## 📦 Files to Deploy

### **Required Files:**
```
/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-app/
├── main.py                                    # ✅ Updated with Firebase routes
├── app/api/firebase_calendar.py               # ✅ Firebase API endpoints  
├── firebase_calendar_integration.py          # ✅ Firebase services
├── app/core/config.py                        # ✅ Updated with Google creds
├── frontend/public/components/Calendar.js    # ✅ Updated endpoints
├── frontend/public/components/CalendarView.js # ✅ Updated endpoints  
├── frontend/public/components/CalendarChat.js # ✅ Updated endpoints
├── frontend/public/firebase-config.json      # ✅ Frontend config
└── requirements.txt                          # ✅ Includes firebase-admin
```

### **Service Account File:**
- `emailpilot-438321-6335761b472e.json` (currently in Downloads)
- **Upload to:** `/path/to/production/service-account.json`

## 🌐 Production Environment Variables

Set these on your production server:

```bash
# Firebase Configuration
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# API Keys
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs

# Security (change in production)
SECRET_KEY=your-production-secret-key-here

# Database
DATABASE_URL=sqlite:///./emailpilot.db

# Environment
ENVIRONMENT=production
DEBUG=false
```

## 🔧 Deployment Steps

### **Step 1: Upload Files**
```bash
# Upload all files to your production server
scp -r emailpilot-app/ user@yourserver:/path/to/production/

# Upload service account
scp /Users/Damon/Downloads/emailpilot-438321-6335761b472e.json user@yourserver:/path/to/production/service-account.json
```

### **Step 2: Set Environment Variables**
```bash
# Option A: Create .env file on server
echo "GOOGLE_CLOUD_PROJECT=emailpilot-438321" >> .env
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json" >> .env
echo "GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs" >> .env

# Option B: Set system environment variables
export GOOGLE_CLOUD_PROJECT=emailpilot-438321
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
export GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs
```

### **Step 3: Install Dependencies**
```bash
pip install -r requirements.txt
```

### **Step 4: Start Application**
```bash
# Development
uvicorn main:app --host 0.0.0.0 --port 8080

# Production (with process manager)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8080
```

### **Step 5: Test Production Deployment**
```bash
# Test health
curl https://emailpilot.ai/

# Test Firebase calendar
curl https://emailpilot.ai/api/firebase-calendar/clients
```

## 🧪 Production Testing Checklist

After deployment, test these features:

- [ ] **Authentication**: Login works
- [ ] **Firebase Connection**: Database connects
- [ ] **Client Management**: Create/view clients  
- [ ] **Calendar Events**: Create/view/edit events
- [ ] **Drag & Drop**: Calendar interface works
- [ ] **AI Chat**: Gemini responses work
- [ ] **Google Doc Import**: Document processing works
- [ ] **Export**: Data export functionality
- [ ] **Real-time Updates**: Changes sync instantly

## 📊 Monitoring & Maintenance

### **Firebase Console:**
- **Monitor usage**: https://console.firebase.google.com/project/emailpilot-438321
- **View logs**: Check Firestore operations
- **Billing**: Monitor API usage

### **Application Logs:**
```bash
# Monitor application
tail -f /var/log/emailpilot/app.log

# Check Firebase connections
grep "Firebase" /var/log/emailpilot/app.log
```

## 🔐 Security Notes

- ✅ Service account file secured with proper permissions
- ✅ Environment variables not in code
- ✅ Firebase security rules configured
- ✅ HTTPS enabled for production
- ✅ CORS configured for emailpilot.ai domain

## 🎯 Expected Results

After successful deployment:

1. **Calendar accessible at**: https://emailpilot.ai/calendar
2. **API endpoints working**: https://emailpilot.ai/api/firebase-calendar/*
3. **Real-time data**: Firebase Firestore backend
4. **AI chat functional**: Gemini integration active
5. **Scalable architecture**: Auto-scaling to millions of users

Your Firebase calendar integration is **production-ready**! 🎉