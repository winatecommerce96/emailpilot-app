import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

// A more advanced card that can fetch its own data
const LiveAdminCard = ({ title, description, endpoint, renderData }) => {
    const [data, setData] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (!endpoint) {
            setIsLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                const response = await fetch(endpoint);
                if (!response.ok) {
                    throw new Error(`Request failed with status ${response.status}`);
                }
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchData();
    }, [endpoint]);

    return (
        <div className="card" style={{ marginBottom: '1rem' }}>
            <h3>{title}</h3>
            <p>{description}</p>
            <div>
                {isLoading && <p>Loading...</p>}
                {error && <p style={{ color: 'red' }}>Error: {error}</p>}
                {data && renderData(data)}
            </div>
        </div>
    );
};

const StaticAdminCard = ({ title, description, linkTo }) => (
    <div className="card" style={{ marginBottom: '1rem' }}>
        <h3>{title}</h3>
        <p>{description}</p>
        {linkTo && <Link to={linkTo}>Go to {title}</Link>}
    </div>
);


export default function Admin() {
    return (
        <div>
            <h2>Admin Dashboard</h2>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
                <LiveAdminCard 
                    title="User Management"
                    description="A count of registered users."
                    endpoint="/api/admin/users"
                    renderData={data => (
                        <p style={{ fontSize: '2rem', fontWeight: 'bold' }}>{data.length} Users</p>
                    )}
                />
                <StaticAdminCard 
                    title="Client Management"
                    description="View and manage client details."
                    linkTo="/dashboard/clients"
                />
                <LiveAdminCard 
                    title="System Status"
                    description="Live status of the backend server."
                    endpoint="/health"
                    renderData={data => (
                        <p style={{ color: data.status === 'ok' ? 'green' : 'red', fontWeight: 'bold' }}>
                            {data.status === 'ok' ? '● Online' : '● Offline'}
                        </p>
                    )}
                />
                <StaticAdminCard 
                    title="Configuration"
                    description="Manage application-level settings and secrets."
                />
            </div>
        </div>
    );
}
