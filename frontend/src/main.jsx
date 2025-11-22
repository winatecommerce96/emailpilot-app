import React from 'react';
import ReactDOM from 'react-dom';
// import { ClerkProvider } from '@clerk/clerk-react';  // DISABLED FOR LOCAL DEV
import App from './App.jsx';

// Import main css file if you have one
// import './index.css';

// BYPASSED: Clerk authentication disabled for local development
// const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
//
// if (!clerkPubKey) {
//   throw new Error('Missing Clerk Publishable Key');
// }

ReactDOM.render(
  <React.StrictMode>
    {/* ClerkProvider removed for local dev */}
    <App />
  </React.StrictMode>,
  document.getElementById('root')
);
