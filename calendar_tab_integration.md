# 📅 Calendar Tab Integration Guide

## 🎯 Integration Overview

The Firebase calendar system needs to be integrated into the existing **Calendar tab** in the EmailPilot.ai application, replacing or enhancing the current calendar functionality.

## 🔧 Integration Approach

### **Option A: Replace Existing Calendar (Recommended)**
Replace the current Calendar tab content with the new Firebase calendar components.

### **Option B: Hybrid Integration** 
Keep existing calendar features and add Firebase calendar as an enhanced view.

## 📁 Files for Calendar Tab Integration

### **Backend Integration (Already Complete):**
- ✅ `main.py` - Firebase calendar routes added
- ✅ `app/api/firebase_calendar.py` - All calendar endpoints
- ✅ `firebase_calendar_integration.py` - Firebase services

### **Frontend Integration Required:**

#### **1. Calendar Tab Component**
Update the existing Calendar tab to use Firebase components:

```javascript
// In the main EmailPilot app Calendar tab
import React from 'react';
import CalendarView from './components/CalendarView.js';
import Calendar from './components/Calendar.js';
import CalendarChat from './components/CalendarChat.js';

function CalendarTab({ currentClient }) {
    return (
        <div className="calendar-tab">
            <div className="calendar-header">
                <h1>📅 Campaign Calendar</h1>
                <p>Plan and manage your email campaigns with AI assistance</p>
            </div>
            
            {/* Main Calendar Interface */}
            <CalendarView 
                clientId={currentClient?.id} 
                clientName={currentClient?.name}
            />
            
            {/* AI Chat Assistant */}
            <CalendarChat 
                clientId={currentClient?.id}
            />
        </div>
    );
}

export default CalendarTab;
```

#### **2. Integration Points:**

**Authentication:**
- ✅ Use existing EmailPilot.ai authentication
- ✅ JWT tokens already compatible

**Client Management:**
- ✅ Use current client context from EmailPilot.ai
- ✅ Firebase calendar will sync with selected client

**Navigation:**
- ✅ Calendar accessible via existing Calendar tab
- ✅ No navigation changes needed

## 🚀 Deployment Steps for Calendar Tab

### **Step 1: Upload Firebase Calendar Files**

Upload to your EmailPilot.ai server:

**Note:** The deployment system will look for `deploy_to_emailpilot.sh` in your package and execute it automatically.
```
/path/to/emailpilot/
├── main.py (updated with Firebase routes)
├── app/api/firebase_calendar.py
├── firebase_calendar_integration.py
└── frontend/calendar/
    ├── CalendarView.js (Firebase-enabled)
    ├── Calendar.js (Firebase-enabled) 
    ├── CalendarChat.js (Firebase-enabled)
    └── EventModal.js
```

### **Step 2: Update Calendar Tab Route**

In your main EmailPilot.ai frontend app:
```javascript
// Calendar tab route
{
    path: '/calendar',
    component: CalendarTab,
    props: { 
        clientId: selectedClient?.id,
        apiEndpoint: '/api/firebase-calendar'
    }
}
```

### **Step 3: Environment Variables**

Add to your production EmailPilot.ai server:
```bash
GOOGLE_CLOUD_PROJECT=emailpilot-438321
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
GEMINI_API_KEY=AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs
```

### **Step 4: Test Integration**

1. **Login to EmailPilot.ai**
2. **Select a client** 
3. **Click Calendar tab**
4. **Verify calendar loads with Firebase data**
5. **Test drag & drop functionality**
6. **Test AI chat features**

## 📊 Calendar Tab Features

### **Available in Calendar Tab:**
- ✅ **Visual Calendar** - Monthly view with drag & drop
- ✅ **Campaign Planning** - Create/edit email campaigns
- ✅ **AI Assistant** - Chat for campaign suggestions
- ✅ **Google Doc Import** - Import campaign plans
- ✅ **Export Options** - Download calendar data
- ✅ **Client Context** - Automatically uses selected client
- ✅ **Real-time Updates** - Instant sync across devices

### **Calendar Tab URL:**
`https://emailpilot.ai/calendar` (existing tab)

## 🔄 Migration Strategy

### **Gradual Migration (Safest):**
1. **Deploy Firebase calendar** alongside existing calendar
2. **Add toggle** between old/new calendar views
3. **Test thoroughly** with existing users
4. **Switch to Firebase** as default once validated
5. **Remove old calendar** after successful migration

### **Direct Migration (Faster):**
1. **Replace Calendar tab** content with Firebase components
2. **Deploy immediately** to production
3. **Test all functionality** in live environment

## 🎯 Integration Result

After integration, your EmailPilot.ai Calendar tab will have:

- **Same URL** - https://emailpilot.ai/calendar
- **Enhanced Functionality** - Firebase-powered features
- **Better Performance** - Real-time sync and scaling
- **AI Integration** - Gemini-powered campaign assistance
- **Seamless UX** - Maintains existing EmailPilot.ai design

## 📋 Integration Checklist

- [ ] Upload Firebase calendar files to production
- [ ] Set environment variables on server
- [ ] Update Calendar tab component
- [ ] Test with existing client selection
- [ ] Verify authentication integration
- [ ] Test all calendar features
- [ ] Monitor Firebase usage
- [ ] Update user documentation

The Firebase calendar is ready to seamlessly integrate into your existing EmailPilot.ai Calendar tab!