# Code Review Summary - 2025-11-16

## Change Summary
This change refactors the frontend authentication to use Clerk instead of a custom solution and introduces a new, feature-rich calendar/holiday management UI with corresponding backend API adjustments.

The migration to Clerk on the frontend is clean and follows best practices. The main areas for improvement are in the new calendar UI's client-side logic and a critical pathing issue in the Python backend.

---

## File: `calendar_master.html`

### 1. `L108`: [HIGH] Holiday import sends individual requests per holiday, leading to poor performance.

**Issue:** The `importHolidays` function iterates through each holiday from the imported file and sends a separate `fetch` request for each one. This will result in a large number of network requests (N+1 problem) for files with many holidays, which is inefficient and may lead to rate-limiting or server-side issues.

**Impact:** Importing a file with 100 holidays will generate 100 separate API calls, creating a poor user experience and unnecessary load on the server.

**Recommendation:** Modify the frontend to send all holidays in a single request to a bulk-processing endpoint. The test script `test_import_buca.py` already uses an endpoint like `/api/calendar/create-bulk-events`, which suggests a bulk mechanism may already exist on the backend.

**Suggested change:**
```javascript
// From
for (const holiday of holidays) {
    if (!holiday.date || !holiday.name) continue;

    await fetch('/api/calendar/holidays/custom', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            date: holiday.date,
            name: holiday.name,
            type: holiday.type || 'custom',
            category: holiday.category || 'custom',
            emoji: holiday.emoji || '📅',
            admin_only: true
        })
    });
}

// To
const response = await fetch('/api/calendar/holidays/custom/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ holidays: holidays })
});

if (!response.ok) {
    throw new Error('Bulk import failed');
}
```

### 2. `L282`: [HIGH] `clearThisMonth` only removes campaigns from the client-side, not the database.

**Issue:** The `clearThisMonth` function filters the `campaigns` array in the local `window.calendarManager` object and saves the result to local storage. It does not make an API call to the backend to delete these campaigns from the persistent database.

**Impact:** The campaigns will reappear the next time the user reloads the page and fetches fresh data from the server, making the "clear" action ineffective.

**Recommendation:** Implement a backend endpoint to handle the deletion of campaigns for a given month and call it from the `clearThisMonth` function.

**Suggested change:**
```javascript
// From
// Clear campaigns for current month
window.calendarManager.campaigns = window.calendarManager.campaigns.filter(c => {
    const campDate = new Date(c.date);
    return campDate.getFullYear() !== year || campDate.getMonth() !== month;
});

window.calendarManager.renderCalendar();
window.calendarManager.saveToLocalStorage();
showToast('Month cleared successfully', 'success');

// To
try {
    const response = await fetch(`/api/calendar/clear-month`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, month })
    });

    if (response.ok) {
        await window.calendarManager.loadHolidaysAndEvents();
        window.calendarManager.renderCalendar();
        showToast('Month cleared successfully', 'success');
    } else {
        showToast('Failed to clear month', 'error');
    }
} catch (error) {
    console.error('Error clearing month:', error);
    showToast('Failed to clear month', 'error');
}
```

### 3. `L43`: [LOW] Not all form fields are cleared after adding a custom holiday.

**Issue:** After successfully adding a new holiday, the `holidayDate`, `holidayName`, and `holidayEmoji` fields are cleared, but the `holidayType` and `holidayCategory` select elements are not reset to their default values.

**Impact:** This could lead to accidentally carrying over the previous type and category when adding the next holiday, which is a minor usability issue.

**Recommendation:** Reset the entire form element to clear all fields. You may need to add an ID to the `<form>` tag (e.g., `id="holiday-form"`) to make this work.

**Suggested change:**
```javascript
// From
document.getElementById('holidayDate').value = '';
document.getElementById('holidayName').value = '';
document.getElementById('holidayEmoji').value = '';

// To
// Assumes the form has been given id="holiday-form"
document.getElementById('holiday-form').reset();
```

---

## File: `main_firestore.py`

### 1. `L142`: [CRITICAL] Hardcoded absolute local path will break the application in other environments.

**Issue:** The line `sys.path.insert(0, '/Users/Damon/klaviyo/klaviyo-audit-automation')` modifies the system path using a hardcoded absolute path on a local machine.

**Impact:** This will cause an `ImportError` for any other developer running the code and in any staging or production deployment environment, making the application non-portable.

**Recommendation:** This line must be removed. The `shared_modules` dependency should be managed as a proper installable package (e.g., from a private PyPI repository) or included as a Git submodule. For local development, a symbolic link or a proper editable install (`pip install -e`) should be used instead of modifying `sys.path`.

**Suggested change:**
```python
# From
import sys
sys.path.insert(0, '/Users/Damon/klaviyo/klaviyo-audit-automation')
# TEMPORARILY DISABLED - causing import hang
# from shared_modules.clients.main import router as multi_platform_clients_router

# To
# TODO: The 'shared_modules' dependency should be installed as a package
# or included as a submodule, not imported via a hardcoded absolute path.
# TEMPORARILY DISABLED - causing import hang
# from shared_modules.clients.main import router as multi_platform_clients_router
```

### 2. `L1110`: [MEDIUM] Serving a file using a relative path is brittle.

**Issue:** The `FileResponse('frontend/public/calendar_master.html')` uses a relative path. The file that is served depends on the current working directory from which the Uvicorn server is launched.

**Impact:** This can lead to a `FileNotFoundError` in different environments (e.g., when running from a different directory, in a Docker container with a different working directory, etc.).

**Recommendation:** Construct an absolute path to the file relative to the `main_firestore.py` file's location to ensure it can always be found regardless of the working directory.

**Suggested change:**
```python
# From
return FileResponse('frontend/public/calendar_master.html')

# To
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(current_dir, 'frontend', 'public', 'calendar_master.html')
return FileResponse(file_path)
```
