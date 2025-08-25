# EmailPilot UI Theming & Logo Documentation

## Overview
The EmailPilot admin interface features a theme-aware logo placement and comprehensive dark/light mode support with automatic system preference detection.

## Logo Implementation

### Location
- **Component**: `/frontend/public/components/AdminSidebarEnhanced.js`
- **Compiled**: `/frontend/public/dist/AdminSidebar.js`
- **Logo URL**: `https://storage.googleapis.com/emailpilot-438321-public/logo.png`

### Placement
- Positioned at the top of the left sidebar navigation
- Left-aligned above the menu panel
- Maintains proportions with responsive sizing:
  - **Expanded state**: max 160px × 60px
  - **Collapsed state**: max 40px × 40px (app mark)

### Behavior
- **Click action**: Routes to main Dashboard (overview tab)
- **Keyboard accessible**: Enter/Space keys trigger navigation
- **Focus indicator**: Blue ring on focus for accessibility
- **Hover effect**: Subtle scale transform (1.05)

## Theme System

### Theme Detection
1. Checks for saved preference in `localStorage('emailpilot-theme')`
2. Falls back to system preference via `prefers-color-scheme` media query
3. Listens for system theme changes and auto-updates (if no manual preference)

### Theme Toggle
- Located below logo in expanded sidebar
- Shows current mode with icon (☀️ Light / 🌙 Dark)
- Persists preference to localStorage
- Smooth transitions (0.3s) for all theme changes

### Theme Styling

#### Light Mode (Default)
```css
--bg-primary: #ffffff
--bg-secondary: #f9fafb
--text-primary: #111827
--text-secondary: #4b5563
--border-primary: #e5e7eb
```

#### Dark Mode
```css
--bg-primary: #111827
--bg-secondary: #1f2937
--text-primary: #f3f4f6
--text-secondary: #9ca3af
--border-primary: #374151
```

### Logo Adaptation
The logo uses adaptive filtering for optimal visibility:

#### Light Mode
- Drop shadow: `0 2px 4px rgba(0, 0, 0, 0.1)`
- No brightness adjustment

#### Dark Mode
- Brightness: `1.2` (20% brighter)
- Drop shadow: `0 2px 8px rgba(59, 130, 246, 0.3)` (blue glow)

## Responsive Behavior

### Desktop (>768px)
- Full sidebar with expanded logo
- Theme toggle visible
- All menu labels shown

### Mobile (<768px)
- Sidebar defaults to collapsed
- Logo shows as app mark (square icon)
- Tooltips on hover for menu items
- Theme toggle hidden when collapsed

### Collapsed State
- Logo resizes to 40×40px app mark
- Maintains click-to-dashboard functionality
- Preserves alt text for screen readers
- Icons-only navigation with tooltips

## Accessibility Features

### Keyboard Navigation
- **Tab order**: Logo → Theme toggle → Menu items
- **Enter/Space**: Activates logo click to dashboard
- **Arrow keys**: Navigate between menu items (when supported)
- **Escape**: Collapse sidebar (when expanded)

### Screen Reader Support
- Descriptive alt text: "EmailPilot Logo - Click to go to dashboard"
- ARIA labels on all interactive elements
- `aria-current="page"` for active menu item
- `aria-expanded` for collapsible groups

### Color Contrast
- Meets WCAG AA standards for all text/background combinations
- Badge colors adjusted for theme (darker backgrounds in dark mode)
- Focus indicators visible in both themes

## How to Update the Logo

### Option 1: Replace Current Logo
1. Upload new logo to Google Cloud Storage bucket
2. Update URL in `/frontend/public/components/AdminSidebarEnhanced.js` line 198
3. Rebuild with `npm run build`

### Option 2: Dual Logo Assets (Light/Dark)
```javascript
// In AdminSidebarEnhanced.js, replace line 198:
src: theme === 'dark' 
  ? 'https://storage.googleapis.com/.../logo-dark.png'
  : 'https://storage.googleapis.com/.../logo-light.png'
```

### Option 3: Local Asset
1. Place logo in `/frontend/public/images/`
2. Reference as `/static/images/logo.png`
3. Ensure proper CORS headers if self-hosting

## CSS Variables Reference

### Using Theme Variables in Components
```javascript
// Access theme variables in React components
const styles = {
  container: {
    backgroundColor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    borderColor: 'var(--border-primary)'
  }
};
```

### Global Theme Classes
- `body.theme-light` - Applied in light mode
- `body.theme-dark` - Applied in dark mode
- `[data-theme="light"]` - HTML attribute for CSS selectors
- `[data-theme="dark"]` - HTML attribute for CSS selectors

## Testing Theme Changes

### Manual Testing
1. Click theme toggle in sidebar
2. Verify logo visibility in both modes
3. Check badge contrast ratios
4. Test collapsed/expanded states
5. Verify theme persists on reload

### Browser Testing
```javascript
// Console commands for testing
localStorage.setItem('emailpilot-theme', 'dark'); location.reload();
localStorage.removeItem('emailpilot-theme'); location.reload();
window.matchMedia('(prefers-color-scheme: dark)').matches; // Check system
```

## Troubleshooting

### Logo Not Visible
- Check network tab for 404 on logo URL
- Verify Google Cloud Storage bucket permissions
- Check filter styles in dark mode

### Theme Not Persisting
- Check localStorage permissions
- Verify no conflicting theme scripts
- Check for JavaScript errors in console

### Contrast Issues
- Use browser DevTools color contrast checker
- Adjust filter brightness for logo if needed
- Modify badge background colors in getBadge()

## Future Enhancements

1. **Auto-detect logo colors**: Use canvas API to detect logo dominant color
2. **Theme scheduling**: Auto-switch based on time of day
3. **Custom themes**: Allow users to create custom color schemes
4. **High contrast mode**: Additional accessibility theme option
5. **SVG logo support**: Better scaling and theme adaptation