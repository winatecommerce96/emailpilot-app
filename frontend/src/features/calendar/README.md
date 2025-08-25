# 📅 EmailPilot Calendar Feature Module

A modern React-based calendar system for campaign planning with AI assistance and revenue goal tracking.

## Features

### 🎯 Core Functionality
- **Monthly Calendar Grid** - Interactive calendar with drag-and-drop events
- **Campaign Management** - Create, edit, delete, and organize campaigns
- **Client Management** - Multi-client support with data isolation
- **Auto-save** - Debounced saving with optimistic UI updates

### 🤖 AI Integration
- **Planning Assistant** - AI-powered campaign suggestions
- **Document Import** - Import campaigns from Google Docs via AI parsing
- **Strategic Recommendations** - Goal-aware planning advice

### 📊 Goals & Analytics
- **Revenue Tracking** - Real-time goal progress visualization
- **Campaign Multipliers** - Different revenue weights by campaign type
- **Achievement Status** - Visual indicators for goal progress
- **Monthly Insights** - Performance analytics and recommendations

### 🎨 Modern UI/UX
- **Responsive Design** - Works on desktop, tablet, and mobile
- **Dark/Light Mode** - Follows system preferences
- **Accessible** - WCAG 2.1 AA compliant
- **Fast Performance** - Optimistic updates and efficient rendering

## Architecture

### Component Structure
```
src/features/calendar/
├── CalendarPage.jsx           # Main page component
├── CalendarBoard.jsx          # Monthly calendar grid
├── CalendarChat.jsx           # AI chat interface
├── modals/
│   └── EventModal.jsx         # Event creation/editing modal
├── services/
│   ├── firebaseCalendar.ts    # Firebase data operations
│   ├── goals.ts               # Revenue goals service
│   └── ai.ts                  # Server-proxied AI calls
├── hooks/
│   └── useCalendarState.ts    # State management hooks
└── types.ts                   # TypeScript definitions
```

### Data Flow
1. **CalendarPage** orchestrates the overall state and handles routing
2. **useCalendarState** manages calendar data, auto-save, and Firebase sync
3. **CalendarBoard** renders the grid and handles user interactions
4. **Services** provide clean APIs for Firebase, goals, and AI operations
5. **EventModal** handles detailed event editing with validation

### State Management
- **Local React State** - UI state and temporary data
- **Custom Hooks** - Reusable state logic and effects
- **Firebase Sync** - Real-time data synchronization
- **Optimistic Updates** - Immediate UI feedback with rollback on errors

## Installation

### 1. Environment Setup
```bash
cp .env.example .env.local
# Edit .env.local with your configuration
```

### 2. Dependencies
The calendar uses only standard React dependencies:
- React 18+
- TypeScript
- Firebase SDK v9+
- TailwindCSS

### 3. Backend Requirements
Ensure these endpoints are available:
- `POST /api/ai/summarize-calendar` - AI document parsing
- `POST /api/ai/chat` - AI planning assistance
- Firebase Firestore access for data persistence

## Usage

### Basic Integration
```jsx
// In your main App.jsx
import CalendarPage from './features/calendar/CalendarPage';

<Route path="/calendar" element={<CalendarPage />} />
```

### Standalone Usage
```jsx
import { CalendarBoard, CalendarChat } from './features/calendar';
import { useCalendarState } from './features/calendar/hooks';

function MyCalendar() {
  const { campaignData, clients, currentClient, actions } = useCalendarState();
  
  return (
    <div>
      <CalendarBoard 
        campaigns={campaignData}
        onCampaignChange={actions.updateCampaign}
        currentClient={currentClient}
      />
      <CalendarChat 
        onAction={actions.applyAIAction}
        campaigns={campaignData}
      />
    </div>
  );
}
```

## Configuration

### Environment Variables
- `REACT_APP_FIREBASE_CONFIG_JSON` - Firebase configuration object
- `REACT_APP_API_BASE` - API base URL for server calls
- `REACT_APP_AI_BASE` - AI service base URL
- `REACT_APP_APP_ID` - Application identifier for Firebase collections

### Feature Flags
- `REACT_APP_ENABLE_AI_CHAT` - Enable/disable AI chat features
- `REACT_APP_ENABLE_DRAG_DROP` - Enable drag-and-drop functionality
- `REACT_APP_ENABLE_GOALS_INTEGRATION` - Enable revenue goals features

## API Integration

### Firebase Collections
```
artifacts/
└── {appId}/
    └── public/
        ├── data/
        │   └── clients/
        │       └── {clientId}/
        │           ├── campaignData: {}
        │           ├── originalCampaignDataAfterImport: {}
        │           └── lastModified: timestamp
        └── goals/
            └── {clientId}/
                ├── monthlyRevenue: number
                ├── year: number
                └── month: number
```

### Server Endpoints
```typescript
// AI endpoints
POST /api/ai/summarize-calendar
{
  docText: string
}
// Returns: Array<{date: string, title: string, content?: string, color?: string}>

POST /api/ai/chat
{
  message: string,
  context: {
    campaigns: Campaign[],
    goals: Goal[],
    clientId: string
  }
}
// Returns: {response: string, suggestions?: string[]}
```

## Customization

### Campaign Types & Colors
Edit the campaign type mappings in `CalendarBoard.jsx`:
```jsx
const campaignTypes = {
  'cheese-club': { color: 'bg-green-200', multiplier: 2.0 },
  'rrb': { color: 'bg-red-200', multiplier: 1.5 },
  // Add custom types...
};
```

### AI Prompts
Customize AI behavior in `services/ai.ts`:
```typescript
const systemPrompt = `You are a marketing calendar assistant...`;
```

### Revenue Calculations
Modify goal calculations in `services/goals.ts`:
```typescript
export function calculateRevenue(campaign: Campaign): number {
  // Custom revenue logic
}
```

## Testing

### Unit Tests
```bash
npm test -- src/features/calendar
```

### Integration Tests
```bash
npm run test:integration calendar
```

### E2E Tests
```bash
npm run test:e2e calendar
```

## Performance

### Optimizations Included
- **React.memo** for expensive components
- **useMemo** for derived state calculations
- **useCallback** for stable event handlers
- **Debounced saves** to prevent API spam
- **Optimistic updates** for responsive UI

### Performance Monitoring
```jsx
import { Profiler } from 'react';

<Profiler id="calendar" onRender={onRenderCallback}>
  <CalendarPage />
</Profiler>
```

## Troubleshooting

### Common Issues

#### Firebase Connection Issues
```javascript
// Check console for Firebase initialization
console.log('Firebase initialized:', !!window.firebase);
```

#### AI Chat Not Working
- Verify `REACT_APP_AI_BASE` is set correctly
- Check server endpoints are deployed
- Ensure CORS is configured for your domain

#### Data Not Saving
- Check browser console for Firebase permissions
- Verify user authentication status
- Check Firestore security rules

### Debug Mode
Enable detailed logging:
```bash
REACT_APP_DEBUG_CALENDAR=true npm start
```

## Contributing

### Code Style
- Use TypeScript for services and utilities
- Use JSX for React components
- Follow existing naming conventions
- Add JSDoc comments for public functions

### Adding Features
1. Create feature branch: `git checkout -b feature/calendar-enhancement`
2. Add components to appropriate folders
3. Update types.ts with new interfaces
4. Add tests for new functionality
5. Update documentation

## License

Part of the EmailPilot application. See main project license.