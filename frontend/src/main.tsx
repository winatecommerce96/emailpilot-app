import React from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { AuthProvider } from '@auth/AuthProvider';
import { ErrorBoundary } from '@components/ErrorBoundary';
import { installDebug } from '@debug/installDebug';
import { DebugOverlay } from '@debug/DebugOverlay';

// Install debug mode before anything else
installDebug();

// Lazy load pages for code splitting
const App = React.lazy(() => import('./App'));
const ClientsPage = React.lazy(() => import('./pages/ClientsPage'));
const CalendarPage = React.lazy(() => import('./pages/CalendarPage'));
const ReportsPage = React.lazy(() => import('./pages/ReportsPage'));
const SettingsPage = React.lazy(() => import('./pages/SettingsPage'));
const LoginPage = React.lazy(() => import('./pages/LoginPage'));
const NotFoundPage = React.lazy(() => import('./pages/NotFoundPage'));

// Create router with all routes
const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorBoundary />,
    children: [
      { index: true, element: <div>Dashboard</div> },
      { path: 'clients', element: <ClientsPage /> },
      { path: 'clients/:clientId', element: <ClientsPage /> },
      { path: 'calendar', element: <CalendarPage /> },
      { path: 'reports', element: <ReportsPage /> },
      { path: 'settings', element: <SettingsPage /> },
    ]
  },
  {
    path: '/login',
    element: <LoginPage />
  },
  {
    path: '*',
    element: <NotFoundPage />
  }
]);

// Mount application
const container = document.getElementById('root');
if (!container) {
  throw new Error('Root element not found');
}

const root = createRoot(container);

root.render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <React.Suspense fallback={
          <div className="flex items-center justify-center min-h-screen">
            <div className="text-lg">Loading...</div>
          </div>
        }>
          <RouterProvider router={router} />
        </React.Suspense>
        <DebugOverlay />
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);