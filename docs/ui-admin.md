# Admin UI Documentation

## Overview
The EmailPilot Admin interface provides a comprehensive dashboard for system management, featuring a collapsible sidebar navigation with dark mode support.

## Admin Sidebar Component

### Architecture
The Admin sidebar uses a defensive architecture with multiple fallback layers:

1. **Error Boundary**: Catches React errors and displays recovery UI
2. **Loading States**: Shows skeleton while data loads
3. **Timeout Protection**: Forces completion after 5 seconds to prevent infinite loading
4. **Retry Logic**: Allows up to 3 retry attempts on failure

### Data Dependencies

The Admin sidebar fetches data from these endpoints:

| Endpoint | Purpose | Required | Fallback |
|----------|---------|----------|----------|
| `/api/admin/system/status` | System health | No | Shows default |
| `/api/agent-config/agents` | AI model counts | No | Hides badge |
| `/api/performance/orders/monitor-all` | Alert counts | No | Hides badge |
| `/api/admin/ops/logs/large` | Large log files | No | Hides badge |

### Loading & Error States

```javascript
// Loading sequence
1. Component mounts → setLoading(true)
2. Data fetch starts (with timeout)
3. Either:
   a. Data loads → setLoading(false)
   b. Timeout (5s) → setLoading(false), setError('timeout')
   c. Fetch fails → setError(error), setLoading(false)
```

### Component States

- **Loading**: Shows skeleton UI with animated placeholders
- **Error**: Shows error message with retry button
- **Loaded**: Shows full sidebar with menu items
- **Collapsed**: Shows icons only (mobile/small screens)

## Menu Structure

```
📊 Core
   ├── Overview - System dashboard
   ├── Users - User management
   └── Clients - Client configuration

📅 Planning  
   ├── Goals - Company goals
   └── Alerts - Order/revenue alerts

🤖 AI & Automation
   ├── MCP - Model Context Protocol
   ├── Chat - AI chat interface
   ├── Models - AI model config
   └── Prompts - Prompt designer

🔌 Integrations
   ├── Slack - Webhook config
   └── OAuth - Service auth

⚙️ System
   ├── Env Vars - Environment config
   ├── Ops & Logs - Operations
   ├── Diagnostics - Health checks
   └── Packages - Package management
```

## Adding New Menu Items

To add a new menu item safely:

1. Edit the `menuGroups` array in `AdminSidebarFixed.js`:

```javascript
const menuGroups = [
  {
    id: 'core',
    label: 'Core',
    icon: '🏠',
    items: [
      { id: 'overview', label: 'Overview', icon: '📊' },
      { id: 'new-item', label: 'New Item', icon: '✨' }, // Add here
    ]
  }
];
```

2. Add badge logic if needed:

```javascript
const getBadge = (tabId) => {
  switch(tabId) {
    case 'new-item':
      if (dataAvailable) {
        return {
          text: count,
          className: 'bg-blue-100 text-blue-800'
        };
      }
      break;
  }
};
```

3. Handle the tab in AdminView:

```javascript
{activeTab === 'new-item' && (
  <NewItemComponent />
)}
```

## Troubleshooting

### Sidebar Not Loading

1. **Check console logs**: Look for `[AdminSidebar]` prefixed messages
2. **Verify script loading**: Ensure `/static/dist/AdminSidebarFixed.js` loads
3. **Check theme**: Verify text isn't white-on-white in dark mode
4. **Network tab**: Check if API calls are failing/redirecting

### Debug Mode

In development (localhost), the sidebar shows debug info at the bottom:
- Mounted state
- Loading state  
- Error messages
- Retry count
- Total menu items

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Perpetual loading | API timeout | Check network, add timeout handling |
| Blank sidebar | Theme conflict | Check CSS, verify dark mode styles |
| Missing badges | Auth failure | Verify token in requests |
| Sidebar resets | Key changes | Use stable React keys |

## CSS Classes

The sidebar respects theme with these key classes:

```css
/* Light mode */
.bg-white
.border-gray-200
.text-gray-900
.hover:bg-gray-100

/* Dark mode */
.dark:bg-gray-800  
.dark:border-gray-700
.dark:text-gray-100
.dark:hover:bg-gray-700
```

## Performance

- Menu items are rendered statically (no async loading)
- Badges update every 3 minutes via polling
- Component uses React.memo to prevent unnecessary re-renders
- Collapsed state persists in localStorage

## Testing

### Manual Tests

1. **Slow network**: Throttle to 3G, sidebar should show skeleton then load
2. **API failure**: Block an endpoint, sidebar should show error with retry
3. **Theme toggle**: Switch themes, text should remain visible
4. **Long session**: Keep open 10+ minutes, should not reset
5. **Resize**: Collapse/expand, state should persist

### Automated Tests

```javascript
// Test loading timeout
jest.useFakeTimers();
render(<AdminSidebarFixed />);
jest.advanceTimersByTime(5000);
expect(screen.queryByText('Loading...')).not.toBeInTheDocument();

// Test error recovery
render(<AdminSidebarFixed />);
fireEvent.click(screen.getByText('Retry'));
expect(screen.getByText('Loading...')).toBeInTheDocument();
```

## Future Improvements

1. **Virtualization**: For large menu lists
2. **Search**: Filter menu items
3. **Favorites**: Pin frequently used items
4. **Keyboard shortcuts**: Quick navigation
5. **Customization**: User-defined menu order