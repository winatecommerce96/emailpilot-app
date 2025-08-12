// Auto-Integration Confirmation Dialog Component
const AutoIntegrationDialog = ({ package_info, onConfirm, onCancel, isVisible }) => {
    const [acknowledged, setAcknowledged] = React.useState(false);
    const [deploymentProgress, setDeploymentProgress] = React.useState(null);
    
    if (!isVisible) return null;
    
    const config = package_info.integration_config || {};
    const downtime = config.estimated_downtime || "30-60 seconds";
    const warnings = config.warnings || [];
    const steps = config.integration_steps || {};
    
    const handleConfirm = async () => {
        if (!acknowledged) {
            alert('Please acknowledge the warnings before proceeding.');
            return;
        }
        
        setDeploymentProgress({
            status: 'starting',
            current_step: 'Preparing deployment...',
            steps_completed: 0,
            total_steps: Object.keys(steps).length,
            logs: ['🚀 Starting auto-integration deployment...']
        });
        
        try {
            // Call the deployment API with auto-integration flag
            const response = await fetch('/api/packages/deploy-with-integration', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    package_id: package_info.id,
                    auto_integration: true,
                    confirmed: true
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                
                // Show real-time progress
                setDeploymentProgress({
                    status: result.status,
                    current_step: 'Deployment in progress...',
                    steps_completed: result.steps?.length || 0,
                    total_steps: Object.keys(steps).length,
                    logs: result.steps?.map(step => 
                        `${step.success ? '✅' : '❌'} ${step.step}: ${step.message || step.error}`
                    ) || []
                });
                
                // Poll for updates if deployment is still running
                if (result.status === 'running') {
                    pollDeploymentStatus(result.deployment_id);
                }
                
            } else {
                throw new Error(`Deployment failed: ${response.statusText}`);
            }
            
        } catch (error) {
            setDeploymentProgress({
                status: 'failed',
                current_step: 'Deployment failed',
                error: error.message,
                logs: ['❌ Deployment failed: ' + error.message]
            });
        }
    };
    
    const pollDeploymentStatus = async (deploymentId) => {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/packages/deployment-status/${deploymentId}`, {
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                    }
                });
                
                if (response.ok) {
                    const status = await response.json();
                    
                    setDeploymentProgress({
                        status: status.status,
                        current_step: status.current_step || 'Processing...',
                        steps_completed: status.steps?.length || 0,
                        total_steps: Object.keys(steps).length,
                        logs: status.steps?.map(step => 
                            `${step.success ? '✅' : '❌'} ${step.step}: ${step.message || step.error}`
                        ) || []
                    });
                    
                    if (status.status === 'completed' || status.status === 'failed') {
                        clearInterval(pollInterval);
                        
                        if (status.status === 'completed') {
                            setTimeout(() => {
                                onConfirm(status);
                            }, 3000); // Show success for 3 seconds then close
                        }
                    }
                }
            } catch (error) {
                clearInterval(pollInterval);
                setDeploymentProgress(prev => ({
                    ...prev,
                    status: 'failed',
                    error: error.message
                }));
            }
        }, 2000); // Poll every 2 seconds
    };
    
    // Show deployment progress instead of confirmation dialog
    if (deploymentProgress) {
        return (
            <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                    <div className="text-center mb-6">
                        <h2 className="text-2xl font-bold text-gray-900 mb-2">
                            {deploymentProgress.status === 'completed' ? '🎉' : 
                             deploymentProgress.status === 'failed' ? '❌' : '🔄'} 
                            Auto-Integration Deployment
                        </h2>
                        
                        <div className="text-lg text-gray-600">
                            {deploymentProgress.current_step}
                        </div>
                        
                        {deploymentProgress.status === 'running' && (
                            <div className="mt-4">
                                <div className="bg-gray-200 rounded-full h-3 overflow-hidden">
                                    <div 
                                        className="bg-blue-600 h-full transition-all duration-500"
                                        style={{
                                            width: `${(deploymentProgress.steps_completed / deploymentProgress.total_steps) * 100}%`
                                        }}
                                    ></div>
                                </div>
                                <div className="text-sm text-gray-500 mt-2">
                                    Step {deploymentProgress.steps_completed} of {deploymentProgress.total_steps}
                                </div>
                            </div>
                        )}
                    </div>
                    
                    {/* Deployment Logs */}
                    <div className="bg-gray-900 text-green-400 p-4 rounded-lg font-mono text-sm max-h-64 overflow-y-auto">
                        {deploymentProgress.logs.map((log, index) => (
                            <div key={index} className="mb-1">
                                {log}
                            </div>
                        ))}
                        
                        {deploymentProgress.status === 'running' && (
                            <div className="text-blue-400 animate-pulse">
                                ⏳ Processing...
                            </div>
                        )}
                    </div>
                    
                    {/* Status Messages */}
                    {deploymentProgress.status === 'completed' && (
                        <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                            <h3 className="font-semibold text-green-800 mb-2">✅ Deployment Successful!</h3>
                            <p className="text-green-700 text-sm">
                                MCP Management System is now fully integrated and operational.
                                The service has been restarted and all endpoints are responding.
                            </p>
                            <p className="text-green-600 text-xs mt-2">
                                This dialog will close automatically in a few seconds...
                            </p>
                        </div>
                    )}
                    
                    {deploymentProgress.status === 'failed' && (
                        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <h3 className="font-semibold text-red-800 mb-2">❌ Deployment Failed</h3>
                            <p className="text-red-700 text-sm">
                                {deploymentProgress.error || 'An error occurred during deployment.'}
                            </p>
                            <p className="text-red-600 text-xs mt-2">
                                Automatic rollback may have been initiated. Check the deployment logs above for details.
                            </p>
                            <button
                                onClick={onCancel}
                                className="mt-3 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                            >
                                Close
                            </button>
                        </div>
                    )}
                </div>
            </div>
        );
    }
    
    return (
        <div className="fixed inset-0 bg-gray-900 bg-opacity-75 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 max-w-3xl w-full max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="text-center mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">
                        ⚠️ Auto-Integration Deployment
                    </h2>
                    <div className="text-lg text-orange-600 font-semibold">
                        Service Restart Required
                    </div>
                </div>
                
                {/* Package Info */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                    <h3 className="font-semibold text-blue-900 mb-2">Package Details</h3>
                    <div className="text-sm text-blue-800">
                        <div>Name: {package_info.name}</div>
                        <div>Version: {config.version || 'Unknown'}</div>
                        <div>Expected Downtime: {downtime}</div>
                    </div>
                </div>
                
                {/* What Will Happen */}
                <div className="mb-6">
                    <h3 className="font-semibold text-gray-900 mb-3">This deployment will automatically:</h3>
                    <div className="space-y-2">
                        {Object.entries(steps).map(([key, step]) => (
                            step.enabled && (
                                <div key={key} className="flex items-start">
                                    <span className="text-green-500 mr-2 mt-0.5">✓</span>
                                    <div className="text-sm">
                                        <div className="font-medium">{step.description}</div>
                                        {step.routes_added && (
                                            <div className="text-gray-500 text-xs mt-1">
                                                Routes: {step.routes_added.join(', ')}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )
                        ))}
                    </div>
                </div>
                
                {/* Warnings */}
                {warnings.length > 0 && (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mb-6">
                        <h3 className="font-semibold text-orange-900 mb-2">⚠️ Important Warnings</h3>
                        <div className="space-y-1">
                            {warnings.map((warning, index) => (
                                <div key={index} className="text-sm text-orange-800">
                                    {warning}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
                
                {/* Acknowledgment */}
                <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
                    <label className="flex items-start">
                        <input
                            type="checkbox"
                            checked={acknowledged}
                            onChange={(e) => setAcknowledged(e.target.checked)}
                            className="mt-1 mr-3"
                        />
                        <div className="text-sm">
                            <div className="font-medium text-gray-900">I understand and acknowledge that:</div>
                            <ul className="mt-2 space-y-1 text-gray-700">
                                <li>• The EmailPilot service will be temporarily unavailable during restart</li>
                                <li>• All active user sessions may be interrupted</li>
                                <li>• A backup will be created automatically for rollback purposes</li>
                                <li>• This deployment will modify core application files</li>
                            </ul>
                        </div>
                    </label>
                </div>
                
                {/* Buttons */}
                <div className="flex justify-end space-x-3">
                    <button
                        onClick={onCancel}
                        className="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!acknowledged}
                        className={`px-6 py-2 rounded-lg ${
                            acknowledged 
                                ? 'bg-orange-600 text-white hover:bg-orange-700' 
                                : 'bg-gray-300 text-gray-500 cursor-not-allowed'
                        }`}
                    >
                        🚀 Proceed with Auto-Integration
                    </button>
                </div>
                
                {/* Footer Info */}
                <div className="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500 text-center">
                    Auto-integration will handle all technical steps automatically.
                    You can monitor progress in real-time during deployment.
                </div>
            </div>
        </div>
    );
};

// Export component
window.AutoIntegrationDialog = AutoIntegrationDialog;