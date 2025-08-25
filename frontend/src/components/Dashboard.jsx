import React from 'react';
import { Routes, Route, Navigate, Link } from 'react-router-dom';
import Calendar from './Calendar.jsx';
import Campaigns from './Campaigns.jsx';
import Goals from './Goals.jsx';
import Admin from './Admin.jsx';
import Clients from './Clients.jsx';

function Navbar({ onLogout }) {
    return (
        <nav style={{ background: 'white', padding: '1rem', boxShadow: '0 2px 4px 0 rgba(0,0,0,0.1)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1280px', margin: '0 auto' }}>
                <div style={{ fontWeight: 'bold' }}>EmailPilot</div>
                <div>
                    <Link to="/dashboard/calendar" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Calendar</Link>
                    <Link to="/dashboard/campaigns" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Campaigns</Link>
                    <Link to="/dashboard/goals" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Goals</Link>
                    <Link to="/dashboard/clients" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Clients</Link>
                    <Link to="/dashboard/admin" style={{ marginRight: '1rem', textDecoration: 'none', color: '#333' }}>Admin</Link>
                    <button onClick={onLogout} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: '#333' }}>Logout</button>
                </div>
            </div>
        </nav>
    );
}

export default function Dashboard() {
    const handleLogout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('session_id');
        window.location.hash = '#/login';
        window.location.reload(); // Force a reload to clear state
    };

    return (
        <div>
            <Navbar onLogout={handleLogout} />
            <main style={{ padding: '2rem' }}>
                <Routes>
                    <Route path="calendar" element={<Calendar />} />
                    <Route path="campaigns" element={<Campaigns />} />
                    <Route path="goals" element={<Goals />} />
                    <Route path="clients" element={<Clients />} />
                    <Route path="admin" element={<Admin />} />
                    {/* Default route for /dashboard */}
                    <Route index element={<Navigate to="calendar" replace />} />
                </Routes>
            </main>
        </div>
    );
}