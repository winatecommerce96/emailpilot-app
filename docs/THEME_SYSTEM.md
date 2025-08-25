# EmailPilot Theme System Documentation

## Overview
EmailPilot now features a global dark/light theme system that applies to the entire application, not just admin sections.

## Changes Made

### 1. Campaign Calendar Removal
- **Removed from Admin Menu**: The "Campaign Calendar" item has been removed from the Planning section in the admin sidebar
- **Routes Cleaned**: All `/admin/calendar` routes and handlers have been removed
- **Code Cleanup**: Calendar loading logic removed from admin view
- **Redirect**: Any attempts to access the old calendar route will redirect to the main admin overview

### 2. Global Theme System

#### Architecture
The theme system is now globally managed with a single source of truth:

```javascript
window.EmailPilotTheme = {
    set(theme)      // Set theme ('light', 'dark', or 'system')
    get()           // Get current effective theme
    toggle()        // Toggle between light and dark
    listen(callback) // Subscribe to theme changes
}
```

#### Theme Application
1. **Early Application**: Theme is applied in `<head>` before any CSS loads to prevent flash
2. **HTML Attribute**: Uses `[data-theme="light|dark"]` on `<html>` element
3. **CSS Variables**: Global CSS variables adapt to theme:
   ```css
   [data-theme="dark"] {
       --bg-primary: #111827;
       --bg-secondary: #1f2937;
       --text-primary: #f3f4f6;
       --text-secondary: #9ca3af;
       --border-primary: #374151;
   }
   ```

#### Persistence
- Theme preference saved to `localStorage` key: `emailpilot-theme`
- Supports three values: `'light'`, `'dark'`, `'system'`
- System preference detected via `prefers-color-scheme` media query

### 3. Components Updated

#### Global Components
- **ThemeToggle**: Reusable toggle button component
- **NavigationEnhanced**: Main navigation with integrated theme toggle
- **AdminSidebar**: Admin sidebar with theme-aware styling

#### Theme Features
- Smooth 300ms transitions between themes
- No flash of wrong theme on page load
- Mobile browser theme-color meta tag updates
- System preference auto-detection
- Manual override persistence

### 4. File Structure

```
/frontend/public/dist/
├── theme-global.js       # Global theme manager
├── theme-early.js        # Early injection script
├── ThemeToggle.js        # Toggle button component
├── NavigationEnhanced.js # Enhanced navigation with theme
└── AdminSidebar.js       # Updated admin sidebar
```

## Usage

### Adding Theme Support to New Components

```javascript
// React component
const MyComponent = () => {
    const [theme, setTheme] = React.useState('light');
    
    React.useEffect(() => {
        // Get initial theme
        setTheme(window.EmailPilotTheme.get());
        
        // Listen for changes
        const unsubscribe = window.EmailPilotTheme.listen((newTheme) => {
            setTheme(newTheme);
        });
        
        return unsubscribe;
    }, []);
    
    // Use theme-aware styles
    const styles = {
        container: {
            backgroundColor: theme === 'dark' ? '#1f2937' : '#ffffff',
            color: theme === 'dark' ? '#f3f4f6' : '#111827'
        }
    };
    
    return React.createElement('div', { style: styles.container }, 'Content');
};
```

### Using CSS Variables

```css
/* Automatically adapts to theme */
.my-component {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    border-color: var(--border-primary);
}
```

### Adding Theme Toggle

```javascript
// Place anywhere in your component
React.createElement(window.ThemeToggle, {
    size: 'medium',      // 'small', 'medium', 'large'
    showLabel: true,     // Show text label
    variant: 'default'   // 'default', 'minimal', 'pill'
})
```

## Testing

### Manual Testing
1. Visit http://localhost:8000
2. Click theme toggle in navigation bar
3. Verify all pages update immediately
4. Refresh page - theme should persist
5. Clear localStorage and refresh - should use system preference

### Verify Campaign Calendar Removal
1. Visit http://localhost:8000/admin
2. Confirm "Campaign Calendar" is not in the menu
3. Try accessing old route (if any) - should redirect

### Theme Persistence Test
```javascript
// Console commands
localStorage.setItem('emailpilot-theme', 'dark'); 
location.reload(); // Should load in dark mode

localStorage.removeItem('emailpilot-theme'); 
location.reload(); // Should use system preference
```

## Migration Notes

### For Existing Components
1. Replace local theme state with global `window.EmailPilotTheme`
2. Use CSS variables instead of hardcoded colors
3. Remove duplicate theme toggle implementations
4. Update conditional styles to check `window.EmailPilotTheme.get()`

### Breaking Changes
- `/admin/calendar` route no longer exists
- Local theme implementations should be migrated to global system
- Components relying on Campaign Calendar need updates

## Future Enhancements
- [ ] Add more theme variants (high contrast, custom colors)
- [ ] Theme scheduling (auto-switch based on time)
- [ ] Per-user theme preferences (saved to backend)
- [ ] Component-specific theme overrides
- [ ] Theme preview before applying