import React from 'react';

export default function Login() {
    const handleLogin = () => {
        window.location.href = '/api/auth/google/login';
    };

    return (
        <div className="card">
            <h1 style={{ marginTop: 0, textAlign: 'center' }}>EmailPilot</h1>
            <p style={{ textAlign: 'center', color: '#6b7280', marginTop: '-5px', marginBottom: '25px' }}>
                The Omnichannel Orchestrator
            </p>
            <button
                onClick={handleLogin}
                style={{
                    width: '100%',
                    padding: '10px',
                    border: 'none',
                    borderRadius: '8px',
                    background: 'linear-gradient(to right, #ff7e5f, #feb47b)',
                    color: 'white',
                    fontSize: '16px',
                    fontWeight: 'bold',
                    cursor: 'pointer',
                    boxShadow: '0 4px 14px 0 rgba(0,0,0,0.1)'
                }}
            >
                Login with Google
            </button>
        </div>
    );
}