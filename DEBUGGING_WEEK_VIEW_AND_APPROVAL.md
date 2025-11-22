# Week View & Approval Page Debugging Guide

## Issues to Resolve

### 1. Week View Time Misalignment
**Problem**: Events scheduled for 10:00 AM are displaying in the 4 AM row (6-hour offset)

### 2. Approval Page Creation 422 Error
**Problem**: Getting "422 Unprocessable Entity" when trying to create client approval page

---

## Debugging Added

### Week View Time Parsing (Lines 12054-12096)

Added comprehensive console logging to trace:
- Raw time values from database (`send_time`, `time` fields)
- Parsed hour and minute values
- AM/PM detection
- Hour conversion logic (12-hour → 24-hour)
- Final position calculation

**How to Debug:**
1. Open browser DevTools → Console
2. Switch to Week view (W key)
3. Look for logs like:
   ```
   [Week View Debug] Campaign: E#11: Last Minute Group Meals, Raw time: "10:00"
     Parsed: hour=10, minute=0, isPM=false, isAM=false
     No AM/PM specified, assuming AM for hour 10
     Final: hour=10, minute=0, topPosition=41.67%
   ```

**Expected Values:**
- 12 AM (midnight) → hour=0, topPosition=0%
- 6 AM → hour=6, topPosition=25%
- 12 PM (noon) → hour=12, topPosition=50%
- 6 PM → hour=18, topPosition=75%
- 10 AM → hour=10, topPosition=41.67%

**If 10 AM shows at 4 AM:**
- Expected: topPosition=41.67% (10 AM)
- Actual: topPosition=16.67% (4 AM)
- This means `hour` is being calculated as `4` instead of `10`

---

### Approval Page Creation (Lines 9237-9272)

Added debugging to:
- Log the complete request payload before sending
- Capture and display the full 422 error response
- Clean up campaign data (remove Angular artifacts, ensure dates are ISO strings)

**How to Debug:**
1. Open browser DevTools → Console
2. Select a client with campaigns
3. Open command palette (Cmd+K or click ⌘)
4. Click "Create Client Approval Page"
5. Look for logs like:
   ```
   [Approval Debug] Request data: {
     "approval_id": "buca-di-beppo-2025-12",
     "client_id": "buca-di-beppo",
     "client_name": "Buca di Beppo",
     "year": 2025,
     "month": 12,
     "campaigns": [...]
   }
   ```

6. If error occurs, check:
   ```
   [Approval Error] Status: 422 Body: {"detail":[...]}
   ```

**Common 422 Causes:**
- `month` sent as string instead of integer → FIXED (now sends `monthInt`)
- `campaigns` array has Date objects instead of ISO strings → FIXED (now converts)
- Missing required fields
- Field type mismatches

---

## Testing Instructions

### Test 1: Week View Time Display

**Steps:**
1. Refresh the calendar page (hard refresh: Cmd+Shift+R)
2. Select "Buca di Beppo" client
3. Navigate to December 2025
4. Switch to Week view (W key)
5. **Open Console** (Cmd+Option+J on Mac, F12 on Windows)
6. Find events scheduled for 10:00 AM

**What to Check:**
- Do the event boxes align with the "10 AM" hour line?
- Check console logs for time parsing
- Note any discrepancies between expected and actual positions

**Take Screenshot:**
- Week view showing misalignment
- Console logs showing time parsing

---

### Test 2: Approval Page Creation

**Steps:**
1. Refresh the calendar page
2. Select "Buca di Beppo" client
3. Navigate to December 2025
4. Ensure there are campaigns visible
5. **Open Console** before starting
6. Open command palette (Cmd+K)
7. Click "Create Client Approval Page"
8. Confirm the dialog

**What to Check:**
- Does the request succeed or fail?
- If it fails, what's the exact error message in console?
- Check `[Approval Debug]` log - is the data structure correct?
- Check `[Approval Error]` log - what does the 422 response say?

**Take Screenshot:**
- Error dialog (if any)
- Console showing `[Approval Debug]` and `[Approval Error]` logs

---

## Next Steps After Testing

### For Week View Issue:

**If time shows as "10:00" but renders at 4 AM:**
- The parsing logic is incorrectly converting "10" to "4"
- May need to check if times are stored in different format in database
- Possible timezone offset issue

**If time shows differently in logs:**
- Database may have wrong values
- Import process may be setting wrong times

### For Approval Page Issue:

**Once we see the console logs, we can identify:**
1. Which field is causing validation error
2. What type/format it expects vs. what we're sending
3. Whether it's a Pydantic model issue or data serialization issue

---

## Files Modified

### frontend/public/calendar_master.html

**Lines 12054-12096**: Added week view time parsing debug logs
- Logs raw time value
- Logs parsed components
- Logs AM/PM detection
- Logs conversion steps
- Logs final position

**Lines 9237-9272**: Added approval page creation debug logs
- Logs complete request payload
- Cleans campaign data (removes non-serializable fields)
- Ensures dates are ISO strings
- Captures and logs full error response

---

## Expected Console Output

### Successful Week View:
```
[Week View Debug] Campaign: E#11: Last Minute Group Meals, Raw time: "10:00 AM"
  Parsed: hour=10, minute=0, isPM=false, isAM=true
  Final: hour=10, minute=0, topPosition=41.67%

[Week View Debug] Campaign: RESEND E#2: Reservations, Raw time: "10:00 AM"
  Parsed: hour=10, minute=0, isPM=false, isAM=true
  Final: hour=10, minute=0, topPosition=41.67%
```

### Successful Approval Creation:
```
[Approval Debug] Request data: {
  "approval_id": "buca-di-beppo-2025-12",
  "client_id": "buca-di-beppo",
  "client_name": "Buca di Beppo",
  "client_slug": "buca-di-beppo",
  "year": 2025,
  "month": 12,
  "month_name": "December",
  "campaigns": [
    {
      "id": "aqNzwfQiPLGiwONjCEX5",
      "name": "E#11: Last Minute Group Meals",
      "date": "2025-12-15T08:00:00.000Z",
      "channel": "email",
      ...
    }
  ],
  "created_at": "2025-11-14T17:45:00.000Z",
  "status": "pending",
  "editable": true
}

✅ Created Asana approval task
```

---

## Status

🔧 **Debug logging added** - Ready for user testing
📊 **Awaiting console output** - Need logs to identify root cause
🎯 **Next**: User tests both features and provides console screenshots

---

**Created**: November 14, 2025
**By**: Claude Code (emailpilot-engineer)
**Purpose**: Diagnose week view misalignment and approval 422 errors
