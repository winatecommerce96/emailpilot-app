# Calendar Master - Quick Reference Guide for New Features

## How to Use New Features

### 1. Resend Campaign (📮)

**What it does:** Creates a duplicate of the campaign scheduled for the next day

**How to use:**
- **Month View:** Hover over any campaign pill → Click "📮" button
- **List View:** Click "📮 Resend" button on any campaign card
- **Result:** New campaign appears next day with "Resend: " prefix and amber border

**Visual Indicators:**
- 🟡 Amber/yellow left border
- ↻ RESEND badge next to campaign name
- Lighter amber gradient background

---

### 2. Week View Navigation

**What it does:** Navigate through weeks in timeline view

**How to use:**
- Click "Week" view button
- Use navigation buttons:
  - **← Prev Week** - Go back one week
  - **Today** - Jump back to current week
  - **Next Week →** - Go forward one week
- OR use keyboard: `←` and `→` arrow keys

**Features:**
- Scrollable timeline (24-hour view)
- Shows campaigns positioned by send time
- Week date range displayed in header

---

### 3. Search/Filter

**What it does:** Filter campaigns by keyword across all views

**How to use:**
- Click search bar at top (or press `/` key)
- Type any keyword
- Campaigns filter in real-time
- Clear search to see all campaigns

**Searches in:**
- Campaign names
- Campaign types
- Segments
- Descriptions

---

### 4. Keyboard Shortcuts

**Quick Actions:**

```
Navigation:
  ←/→         Navigate weeks/months
  M           Month view
  W           Week view  
  L           List view

Actions:
  N           New campaign
  /           Focus search
  Ctrl/Cmd+S  Save to cloud
  ESC         Close modals
  ?           Show all shortcuts

Power User:
  Ctrl/Cmd+T  Toggle theme
  Ctrl/Cmd+K  Command palette
```

**To see full list:** Press `?` key anytime

---

## Visual Changes Summary

### Campaign Pills (Month View)
```
Before:
[📧 Campaign Name                    ]
[Duplicate][Edit][Delete]

After:
[📧 Campaign Name                    ] ← Hover to see actions
[Duplicate][📮 Resend][Edit][Delete]

Resend campaigns:
[📧 Resend: Campaign Name ↻ RESEND   ] ← Amber border
```

### Week View Header
```
Before:
📅 Week View
Aug 10 - Aug 16, 2025

After:
📅 Week View
[← Prev Week] [Today] [Next Week →]
Aug 10 - Aug 16, 2025
```

### Top Section
```
Before:
[Campaign Types & Segments Legend]

After:
[Search campaigns... (Press / to focus)]
[Campaign Types & Segments Legend]
```

---

## Technical Details

### New Functions (Developer Reference)

```javascript
// Resend feature
calendarManager.resendCampaign(campaignId)

// Week navigation
previousWeek()
nextWeek()
goToCurrentWeek()

// Search
filterEvents(query)

// Keyboard shortcuts help
toggleShortcutsModal()
```

### New Data Properties

```javascript
// Campaign object additions
{
  is_resend: true,  // Flag for resend campaigns
  // ... existing properties
}
```

### Global Variables

```javascript
currentWeekOffset  // Tracks week offset (0 = current week)
searchQuery        // Current search filter string
```

---

## Compatibility Notes

- ✅ Works with existing Firestore sync
- ✅ Multi-window updates work
- ✅ No data migration needed
- ✅ Backward compatible with old campaigns
- ✅ All existing features preserved

---

## Troubleshooting

**Resend button not appearing?**
- Hover over campaign pill in month view
- Check you're using updated calendar_master.html

**Week navigation not working?**
- Ensure you're in Week view (click "Week" button)
- Try clicking "Today" to reset

**Search not filtering?**
- Check you typed in the search box (not browser search)
- Search is case-insensitive
- Clear search by deleting all text

**Keyboard shortcuts not working?**
- Make sure you're not typing in an input field
- Try clicking somewhere on the calendar first
- Press `?` to see if shortcuts modal opens

**To rollback all changes:**
```bash
cd frontend/public
cp calendar_master.html.backup calendar_master.html
```

---

## Performance Notes

- Search is client-side (instant, no API calls)
- Week navigation doesn't reload data
- Resend creates new campaign (syncs to Firestore)
- No performance impact on large calendars

---

## Future Enhancements (Not Yet Implemented)

- Keyboard shortcut `R` for resend
- Right-click context menu
- Batch resend multiple campaigns
- Custom date selection for resend
- Search history/autocomplete
- Advanced filter combinations

---

*Quick Reference v1.0 | 2025-11-13*
