import React, { useState, useEffect } from 'react';

export default function Clients() {
    const [clients, setClients] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchClients = async () => {
            try {
                const response = await fetch('/api/clients/');
                if (!response.ok) {
                    throw new Error('Failed to fetch clients');
                }
                const data = await response.json();
                setClients(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setIsLoading(false);
            }
        };

        fetchClients();
    }, []);

    if (isLoading) {
        return <div className="card"><h2>Loading Clients...</h2></div>;
    }

    if (error) {
        return <div className="card"><h2>Error</h2><p>{error}</p></div>;
    }

    return (
        <div className="card">
            <h2>Clients</h2>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                    <tr>
                        <th style={{ borderBottom: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>Name</th>
                        <th style={{ borderBottom: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>Website</th>
                        <th style={{ borderBottom: '1px solid #ddd', padding: '8px', textAlign: 'left' }}>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {clients.map(client => (
                        <tr key={client.id}>
                            <td style={{ borderBottom: '1px solid #ddd', padding: '8px' }}>{client.name}</td>
                            <td style={{ borderBottom: '1px solid #ddd', padding: '8px' }}><a href={client.website} target="_blank" rel="noopener noreferrer">{client.website}</a></td>
                            <td style={{ borderBottom: '1px solid #ddd', padding: '8px' }}>{client.is_active ? 'Active' : 'Inactive'}</td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}
