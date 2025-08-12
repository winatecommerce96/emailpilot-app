// Simple CalendarView Component (No JSX, No Babel needed)
(function() {
    'use strict';
    
    const { useState, useEffect } = React;
    const e = React.createElement;
    
    // API configuration
    const API_BASE_URL = window.API_BASE_URL || '';
    
    function CalendarViewSimple() {
        const [loading, setLoading] = useState(true);
        const [error, setError] = useState(null);
        const [clients, setClients] = useState([]);
        const [selectedClient, setSelectedClient] = useState(null);
        const [importing, setImporting] = useState(false);
        const [currentMonth, setCurrentMonth] = useState(new Date());
        
        useEffect(() => {
            loadClients();
        }, []);
        
        const loadClients = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`${API_BASE_URL}/api/clients/`, {
                    withCredentials: true
                });
                setClients(response.data || []);
                if (response.data && response.data.length > 0) {
                    setSelectedClient(response.data[0]);
                }
                setError(null);
            } catch (err) {
                console.error('Error loading clients:', err);
                setError('Failed to load clients: ' + err.message);
            } finally {
                setLoading(false);
            }
        };
        
        const handleGoogleDocImport = async () => {
            if (!selectedClient) {
                alert('Please select a client first');
                return;
            }
            
            setImporting(true);
            try {
                // In a real implementation, you would use Google's OAuth flow here
                const docId = prompt('Enter Google Doc ID:');
                const accessToken = prompt('Enter access token (in production, this would be handled by OAuth):');
                
                if (docId && accessToken) {
                    await axios.post(`${API_BASE_URL}/api/calendar/import/google-doc`, {
                        client_id: selectedClient.id,
                        doc_id: docId,
                        access_token: accessToken
                    }, { withCredentials: true });
                    
                    alert('Import started! Please check back in a moment.');
                    // Refresh calendar data
                    loadClients();
                }
            } catch (error) {
                alert('Import failed: ' + (error.response?.data?.detail || 'Unknown error'));
            } finally {
                setImporting(false);
            }
        };
        
        if (error) {
            return e('div', { className: 'p-8 text-center' },
                e('div', { className: 'text-red-600 mb-4' }, '❌ Error'),
                e('p', { className: 'text-sm text-gray-600 mb-4' }, error),
                e('button', {
                    onClick: loadClients,
                    className: 'px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700'
                }, 'Try Again')
            );
        }
        
        if (loading) {
            return e('div', { className: 'p-8 text-center' },
                e('div', { className: 'animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600 mx-auto' }),
                e('p', { className: 'mt-2 text-sm text-gray-500' }, 'Loading calendar...')
            );
        }
        
        if (clients.length === 0) {
            return e('div', { className: 'p-8 text-center' },
                e('p', { className: 'text-gray-500' }, 'No clients available. Please add clients first.')
            );
        }
        
        return e('div', { className: 'p-8' },
            e('div', { className: 'flex justify-between items-center mb-4' },
                e('h2', { className: 'text-2xl font-bold' }, 'Campaign Calendar'),
                selectedClient && e('div', { className: 'text-sm text-gray-600' }, 
                    'Client: ' + selectedClient.name
                )
            ),
            e('div', { className: 'mb-4' },
                e('label', { className: 'block text-sm font-medium text-gray-700 mb-2' }, 'Select Client:'),
                e('select', {
                    className: 'block w-full px-3 py-2 border border-gray-300 rounded-md',
                    value: selectedClient ? String(selectedClient.id) : '',
                    onChange: (evt) => {
                        const clientId = evt.target.value;
                        console.log('Select value changed to:', clientId);
                        console.log('Available clients:', clients.map(c => ({ id: c.id, name: c.name })));
                        
                        if (clientId) {
                            const client = clients.find(c => String(c.id) === clientId);
                            console.log('Found client:', client);
                            setSelectedClient(client);
                        } else {
                            setSelectedClient(null);
                        }
                    }
                }, 
                    [e('option', { key: 'default', value: '' }, 'Select a client...')].concat(
                        clients.map(client => 
                            e('option', { key: client.id, value: String(client.id) }, client.name)
                        )
                    )
                )
            ),
            selectedClient && e('div', { className: 'bg-white rounded-lg shadow' },
                // Calendar Header
                e('div', { className: 'px-6 py-4 border-b border-gray-200' },
                    e('div', { className: 'flex justify-between items-center' },
                        e('h3', { className: 'text-lg font-semibold text-gray-900' }, 
                            currentMonth.toLocaleString('default', { month: 'long', year: 'numeric' })
                        ),
                        e('div', { className: 'flex items-center space-x-2' },
                            e('button', {
                                onClick: handleGoogleDocImport,
                                disabled: importing || !selectedClient,
                                className: 'px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed'
                            }, importing ? 'Importing...' : 'Import from Google Doc'),
                            e('button', { 
                                className: 'p-2 hover:bg-gray-100 rounded',
                                onClick: () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() - 1))
                            }, '←'),
                            e('button', { 
                                className: 'p-2 hover:bg-gray-100 rounded',
                                onClick: () => setCurrentMonth(new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1))
                            }, '→')
                        )
                    )
                ),
                // Calendar Grid
                e('div', { className: 'p-6' },
                    // Day headers
                    e('div', { className: 'grid grid-cols-7 gap-0 mb-2' },
                        ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map(day =>
                            e('div', { 
                                key: day, 
                                className: 'text-center text-xs font-semibold text-gray-600 py-2' 
                            }, day)
                        )
                    ),
                    // Calendar days
                    e('div', { className: 'grid grid-cols-7 gap-0 border-l border-t border-gray-200' },
                        // Generate calendar days dynamically based on current month
                        (() => {
                            const year = currentMonth.getFullYear();
                            const month = currentMonth.getMonth();
                            const firstDay = new Date(year, month, 1).getDay();
                            const daysInMonth = new Date(year, month + 1, 0).getDate();
                            const totalCells = 42; // 6 weeks
                            
                            return Array.from({ length: totalCells }, (_, i) => {
                                const dayNum = i - firstDay + 1;
                                const isCurrentMonth = dayNum >= 1 && dayNum <= daysInMonth;
                                const dayDisplay = isCurrentMonth ? dayNum : '';
                                
                                return e('div', { 
                                    key: i,
                                    className: 'border-r border-b border-gray-200 min-h-[100px] p-2 ' +
                                        (isCurrentMonth ? 'bg-white hover:bg-gray-50' : 'bg-gray-50')
                                },
                                    e('div', { className: 'text-sm text-gray-600 mb-1' }, dayDisplay),
                                    // Placeholder for events
                                    isCurrentMonth && dayNum === 15 && e('div', {
                                        className: 'text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded mb-1 cursor-pointer'
                                    }, 'Sample Event'),
                                    isCurrentMonth && dayNum === 20 && e('div', {
                                        className: 'text-xs bg-green-100 text-green-700 px-2 py-1 rounded cursor-pointer'
                                    }, 'Campaign Launch')
                                );
                            });
                        })()
                    ),
                    e('div', { className: 'mt-4 text-sm text-gray-500 text-center' },
                        'Full calendar with drag-and-drop functionality loading...'
                    )
                )
            )
        );
    }
    
    // Make it available globally
    window.CalendarViewSimple = CalendarViewSimple;
})();