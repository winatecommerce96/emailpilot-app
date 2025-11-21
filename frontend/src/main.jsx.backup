import React from 'react';
import ReactDOM from 'react-dom';
import { ClerkProvider } from '@clerk/clerk-react';
import App from './App.jsx';

// Import main css file if you have one
// import './index.css';

// Get Clerk publishable key from environment
const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

if (!clerkPubKey) {
  throw new Error('Missing Clerk Publishable Key');
}

ReactDOM.render(
  <React.StrictMode>
    <ClerkProvider publishableKey={clerkPubKey}>
      <App />
    </ClerkProvider>
  </React.StrictMode>,
  document.getElementById('root')
);
