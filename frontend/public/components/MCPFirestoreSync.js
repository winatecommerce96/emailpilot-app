// MCP Firestore Synchronization Component
const MCPFirestoreSync = () => {
    const [syncStatus, setSyncStatus] = React.useState(null);
    const [firestoreClients, setFirestoreClients] = React.useState([]);
    const [loading, setLoading] = React.useState(false);
    const [showFirestoreClients, setShowFirestoreClients] = React.useState(false);
    const [autoSyncEnabled, setAutoSyncEnabled] = React.useState(false);

    React.useEffect(() => {
        checkSyncStatus();
    }, []);

    const checkSyncStatus = async () => {
        try {
            const response = await fetch('/api/mcp-firestore/sync/status', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            if (response.ok) {
                const status = await response.json();
                setSyncStatus(status);
            }
        } catch (error) {
            console.error('Error checking sync status:', error);
        }
    };

    const syncToFirestore = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/mcp-firestore/sync/to-firestore', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Successfully synced ${result.details.synced} clients to Firestore`);
                checkSyncStatus();
            } else {
                const error = await response.json();
                alert(`Sync failed: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error syncing to Firestore:', error);
            alert('Failed to sync to Firestore');
        } finally {
            setLoading(false);
        }
    };

    const syncFromFirestore = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/mcp-firestore/sync/from-firestore', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Imported ${result.details.imported} new clients, updated ${result.details.updated} existing clients`);
                // Reload the main MCP clients list
                if (window.location.href.includes('mcp')) {
                    window.location.reload();
                }
            } else {
                const error = await response.json();
                alert(`Import failed: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error importing from Firestore:', error);
            alert('Failed to import from Firestore');
        } finally {
            setLoading(false);
        }
    };

    const loadFirestoreClients = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/mcp-firestore/firestore-clients', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                const data = await response.json();
                setFirestoreClients(data.clients);
                setShowFirestoreClients(true);
            }
        } catch (error) {
            console.error('Error loading Firestore clients:', error);
        } finally {
            setLoading(false);
        }
    };

    const enableRealtimeSync = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/mcp-firestore/sync/enable-realtime', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                setAutoSyncEnabled(true);
                alert('Real-time synchronization enabled');
            }
        } catch (error) {
            console.error('Error enabling real-time sync:', error);
        } finally {
            setLoading(false);
        }
    };

    const autoPopulate = async () => {
        if (!confirm('This will sync all MCP clients between local database and Firestore. Continue?')) {
            return;
        }
        
        setLoading(true);
        try {
            const response = await fetch('/api/mcp-firestore/sync/auto-populate', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                alert(`Auto-population completed!\n` +
                      `Imported: ${result.import_result.imported} clients\n` +
                      `Updated: ${result.import_result.updated} clients\n` +
                      `Synced to Firestore: ${result.sync_result.synced} clients\n` +
                      `Real-time sync: ${result.realtime_sync}`);
                
                // Reload the page to show updated clients
                window.location.reload();
            } else {
                const error = await response.json();
                alert(`Auto-population failed: ${error.detail}`);
            }
        } catch (error) {
            console.error('Error in auto-population:', error);
            alert('Failed to auto-populate clients');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Firestore Synchronization</h3>
                <button
                    onClick={checkSyncStatus}
                    className="text-sm text-blue-600 hover:text-blue-800"
                    disabled={loading}
                >
                    Refresh Status
                </button>
            </div>

            {/* Sync Status */}
            {syncStatus && (
                <div className="mb-4 p-3 bg-gray-50 rounded">
                    <div className="text-sm">
                        <div className="flex items-center mb-2">
                            <span className="font-medium mr-2">Sync Enabled:</span>
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                syncStatus.sync_enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                                {syncStatus.sync_enabled ? 'Yes' : 'No'}
                            </span>
                        </div>
                        <div className="flex items-center mb-2">
                            <span className="font-medium mr-2">Firestore Connected:</span>
                            <span className={`px-2 py-1 rounded text-xs font-semibold ${
                                syncStatus.firestore_connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                            }`}>
                                {syncStatus.firestore_connected ? 'Connected' : 'Disconnected'}
                            </span>
                        </div>
                        <div className="flex items-center">
                            <span className="font-medium mr-2">Project ID:</span>
                            <span className="text-gray-600">{syncStatus.project_id}</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Quick Actions */}
            <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Quick Actions</h4>
                <div className="grid grid-cols-2 gap-2">
                    <button
                        onClick={autoPopulate}
                        className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:opacity-50"
                        disabled={loading || !syncStatus?.firestore_connected}
                    >
                        {loading ? 'Processing...' : '🔄 Auto-Populate Clients'}
                    </button>
                    <button
                        onClick={enableRealtimeSync}
                        className={`px-4 py-2 rounded disabled:opacity-50 ${
                            autoSyncEnabled 
                                ? 'bg-green-100 text-green-800 cursor-default' 
                                : 'bg-blue-600 text-white hover:bg-blue-700'
                        }`}
                        disabled={loading || autoSyncEnabled || !syncStatus?.firestore_connected}
                    >
                        {autoSyncEnabled ? '✓ Real-time Sync Active' : '⚡ Enable Real-time Sync'}
                    </button>
                </div>
            </div>

            {/* Manual Sync Options */}
            <div className="mb-4">
                <h4 className="text-sm font-medium mb-2">Manual Synchronization</h4>
                <div className="flex space-x-2">
                    <button
                        onClick={syncToFirestore}
                        className="bg-blue-500 text-white px-3 py-1 rounded text-sm hover:bg-blue-600 disabled:opacity-50"
                        disabled={loading || !syncStatus?.firestore_connected}
                    >
                        Push to Firestore →
                    </button>
                    <button
                        onClick={syncFromFirestore}
                        className="bg-green-500 text-white px-3 py-1 rounded text-sm hover:bg-green-600 disabled:opacity-50"
                        disabled={loading || !syncStatus?.firestore_connected}
                    >
                        ← Pull from Firestore
                    </button>
                    <button
                        onClick={loadFirestoreClients}
                        className="bg-gray-500 text-white px-3 py-1 rounded text-sm hover:bg-gray-600 disabled:opacity-50"
                        disabled={loading || !syncStatus?.firestore_connected}
                    >
                        View Firestore Clients
                    </button>
                </div>
            </div>

            {/* Firestore Clients List */}
            {showFirestoreClients && (
                <div className="mt-4 border-t pt-4">
                    <div className="flex justify-between items-center mb-2">
                        <h4 className="text-sm font-medium">Firestore MCP Clients ({firestoreClients.length})</h4>
                        <button
                            onClick={() => setShowFirestoreClients(false)}
                            className="text-sm text-gray-500 hover:text-gray-700"
                        >
                            Hide
                        </button>
                    </div>
                    <div className="max-h-60 overflow-y-auto">
                        <table className="min-w-full text-sm">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-3 py-2 text-left">Name</th>
                                    <th className="px-3 py-2 text-left">Account ID</th>
                                    <th className="px-3 py-2 text-left">Status</th>
                                    <th className="px-3 py-2 text-left">Provider</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200">
                                {firestoreClients.map((client, index) => (
                                    <tr key={client.firestore_id || index}>
                                        <td className="px-3 py-2">{client.name}</td>
                                        <td className="px-3 py-2 text-xs text-gray-500">{client.account_id}</td>
                                        <td className="px-3 py-2">
                                            <span className={`px-1 py-0.5 text-xs rounded ${
                                                client.enabled ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                                            }`}>
                                                {client.enabled ? 'Enabled' : 'Disabled'}
                                            </span>
                                        </td>
                                        <td className="px-3 py-2 text-xs">{client.default_model_provider}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Help Text */}
            <div className="mt-4 text-xs text-gray-500">
                <p className="mb-1">• <strong>Auto-Populate:</strong> Syncs all MCP clients between local database and Firestore</p>
                <p className="mb-1">• <strong>Real-time Sync:</strong> Automatically syncs changes between databases</p>
                <p>• <strong>Manual Sync:</strong> Push local changes to Firestore or pull Firestore changes locally</p>
            </div>
        </div>
    );
};

// Export component
window.MCPFirestoreSync = MCPFirestoreSync;