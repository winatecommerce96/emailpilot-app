import React from 'react';
import { SignIn } from '@clerk/clerk-react';

export default function Login() {
    return (
        <div className="card">
            <h1 style={{ marginTop: 0, textAlign: 'center' }}>EmailPilot</h1>
            <p style={{ textAlign: 'center', color: '#6b7280', marginTop: '-5px', marginBottom: '25px' }}>
                The Omnichannel Orchestrator
            </p>
            <div style={{ display: 'flex', justifyContent: 'center', marginTop: '20px' }}>
                <SignIn />
            </div>
        </div>
    );
}