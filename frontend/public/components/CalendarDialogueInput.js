/**
 * Calendar Dialogue Input Component
 * Allows users to provide additional context/notes for AI calendar generation
 */

class CalendarDialogueInput extends React.Component {
    constructor(props) {
        super(props);
        this.state = {
            dialogueText: '',
            isProcessing: false,
            orchestrationResult: null,
            error: null,
            showAdvanced: false,
            streamingMessages: []
        };
    }

    handleTextChange = (e) => {
        this.setState({ dialogueText: e.target.value });
    };

    handleOrchestrateCalendar = async () => {
        const { clientId, month, onCalendarGenerated } = this.props;
        const { dialogueText } = this.state;

        if (!clientId || !month) {
            this.setState({ error: 'Client ID and month are required' });
            return;
        }

        this.setState({ 
            isProcessing: true, 
            error: null, 
            orchestrationResult: null,
            streamingMessages: [] 
        });

        try {
            // Use streaming endpoint for real-time updates
            if (this.state.showAdvanced) {
                await this.orchestrateWithStream(clientId, month, dialogueText);
            } else {
                // Use standard endpoint
                const response = await fetch('/api/calendar/v2/orchestrate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('authToken')}`
                    },
                    body: JSON.stringify({
                        client_id: clientId,
                        month: month,
                        dialogue_input: dialogueText,
                        include_historical: true,
                        include_recent: true,
                        use_ai_planning: true
                    })
                });

                if (!response.ok) {
                    throw new Error(`Orchestration failed: ${response.statusText}`);
                }

                const result = await response.json();
                
                this.setState({ 
                    orchestrationResult: result,
                    isProcessing: false 
                });

                // Notify parent component
                if (onCalendarGenerated && result.success) {
                    onCalendarGenerated(result);
                }

                // Show success message
                this.showSuccessMessage(result);
            }
        } catch (error) {
            console.error('Orchestration error:', error);
            this.setState({ 
                error: error.message,
                isProcessing: false 
            });
        }
    };

    orchestrateWithStream = async (clientId, month, dialogueText) => {
        const eventSource = new EventSource('/api/calendar/v2/orchestrate/stream?' + 
            new URLSearchParams({
                client_id: clientId,
                month: month,
                dialogue_input: dialogueText || ''
            }));

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.event === 'progress') {
                this.setState(prevState => ({
                    streamingMessages: [...prevState.streamingMessages, data.message]
                }));
            } else if (data.event === 'completed') {
                this.setState({
                    orchestrationResult: data.result,
                    isProcessing: false
                });
                eventSource.close();
                
                if (this.props.onCalendarGenerated && data.result.success) {
                    this.props.onCalendarGenerated(data.result);
                }
                
                this.showSuccessMessage(data.result);
            } else if (data.event === 'error') {
                this.setState({
                    error: data.message,
                    isProcessing: false
                });
                eventSource.close();
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            this.setState({
                error: 'Connection lost. Please try again.',
                isProcessing: false
            });
            eventSource.close();
        };
    };

    showSuccessMessage = (result) => {
        const message = `✅ Calendar generated successfully! 
            ${result.total_campaigns} campaigns planned with 
            $${result.expected_revenue.toLocaleString()} expected revenue.`;
        
        // Use existing notification system if available
        if (window.showNotification) {
            window.showNotification(message, 'success');
        } else {
            alert(message);
        }
    };

    toggleAdvanced = () => {
        this.setState({ showAdvanced: !this.state.showAdvanced });
    };

    render() {
        const { 
            dialogueText, 
            isProcessing, 
            orchestrationResult, 
            error, 
            showAdvanced,
            streamingMessages 
        } = this.state;

        return React.createElement('div', { className: 'calendar-dialogue-input bg-white rounded-lg shadow-md p-6 mb-6' },
            // Header
            React.createElement('div', { className: 'flex items-center justify-between mb-4' },
                React.createElement('h3', { className: 'text-lg font-semibold text-gray-800' },
                    '🤖 AI Calendar Orchestrator'
                ),
                React.createElement('button', {
                    onClick: this.toggleAdvanced,
                    className: 'text-sm text-blue-600 hover:text-blue-800'
                }, showAdvanced ? 'Simple Mode' : 'Advanced Mode')
            ),

            // Description
            React.createElement('p', { className: 'text-sm text-gray-600 mb-4' },
                'Provide additional context or specific requirements for your campaign calendar. ' +
                'The AI will incorporate your notes into the planning process.'
            ),

            // Textarea for dialogue input
            React.createElement('div', { className: 'mb-4' },
                React.createElement('label', { 
                    htmlFor: 'dialogue-input',
                    className: 'block text-sm font-medium text-gray-700 mb-2'
                }, 'Additional Context & Notes (Optional):'),
                React.createElement('textarea', {
                    id: 'dialogue-input',
                    value: dialogueText,
                    onChange: this.handleTextChange,
                    placeholder: 'Example: Focus on holiday promotions, include Black Friday campaign, emphasize new product launches...',
                    className: 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500',
                    rows: 4,
                    disabled: isProcessing
                })
            ),

            // Example prompts
            React.createElement('div', { className: 'mb-4' },
                React.createElement('p', { className: 'text-xs text-gray-500 mb-2' }, 'Quick prompts:'),
                React.createElement('div', { className: 'flex flex-wrap gap-2' },
                    ['Holiday focus', 'Product launch', 'VIP campaigns', 'Seasonal themes'].map(prompt =>
                        React.createElement('button', {
                            key: prompt,
                            onClick: () => this.setState({ 
                                dialogueText: dialogueText ? dialogueText + ', ' + prompt : prompt 
                            }),
                            className: 'text-xs px-2 py-1 bg-gray-100 hover:bg-gray-200 rounded',
                            disabled: isProcessing
                        }, prompt)
                    )
                )
            ),

            // Advanced options (if shown)
            showAdvanced && React.createElement('div', { className: 'mb-4 p-3 bg-gray-50 rounded' },
                React.createElement('h4', { className: 'text-sm font-medium mb-2' }, 'Advanced Options'),
                React.createElement('div', { className: 'space-y-2' },
                    React.createElement('label', { className: 'flex items-center text-sm' },
                        React.createElement('input', { 
                            type: 'checkbox', 
                            defaultChecked: true,
                            className: 'mr-2'
                        }),
                        'Include 6-month historical analysis'
                    ),
                    React.createElement('label', { className: 'flex items-center text-sm' },
                        React.createElement('input', { 
                            type: 'checkbox', 
                            defaultChecked: true,
                            className: 'mr-2'
                        }),
                        'Include 30-day performance analysis'
                    ),
                    React.createElement('label', { className: 'flex items-center text-sm' },
                        React.createElement('input', { 
                            type: 'checkbox', 
                            defaultChecked: true,
                            className: 'mr-2'
                        }),
                        'Use AI for campaign planning'
                    )
                )
            ),

            // Streaming messages (if in advanced mode)
            showAdvanced && streamingMessages.length > 0 && React.createElement('div', { 
                className: 'mb-4 p-3 bg-blue-50 rounded max-h-32 overflow-y-auto'
            },
                React.createElement('div', { className: 'text-xs text-gray-600' },
                    streamingMessages.map((msg, idx) =>
                        React.createElement('div', { key: idx, className: 'mb-1' },
                            `• ${msg}`
                        )
                    )
                )
            ),

            // Generate button
            React.createElement('button', {
                onClick: this.handleOrchestrateCalendar,
                disabled: isProcessing,
                className: `w-full py-2 px-4 rounded-md font-medium transition-colors ${
                    isProcessing 
                        ? 'bg-gray-400 cursor-not-allowed' 
                        : 'bg-blue-600 hover:bg-blue-700 text-white'
                }`
            },
                isProcessing ? (
                    React.createElement('span', { className: 'flex items-center justify-center' },
                        React.createElement('svg', { 
                            className: 'animate-spin -ml-1 mr-3 h-5 w-5 text-white',
                            xmlns: 'http://www.w3.org/2000/svg',
                            fill: 'none',
                            viewBox: '0 0 24 24'
                        },
                            React.createElement('circle', {
                                className: 'opacity-25',
                                cx: '12',
                                cy: '12',
                                r: '10',
                                stroke: 'currentColor',
                                strokeWidth: '4'
                            }),
                            React.createElement('path', {
                                className: 'opacity-75',
                                fill: 'currentColor',
                                d: 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z'
                            })
                        ),
                        'Orchestrating Calendar...'
                    )
                ) : '🚀 Generate AI Calendar'
            ),

            // Error display
            error && React.createElement('div', { 
                className: 'mt-4 p-3 bg-red-50 border border-red-200 rounded-md'
            },
                React.createElement('p', { className: 'text-sm text-red-600' }, `Error: ${error}`)
            ),

            // Success result display
            orchestrationResult && orchestrationResult.success && React.createElement('div', { 
                className: 'mt-4 p-4 bg-green-50 border border-green-200 rounded-md'
            },
                React.createElement('h4', { className: 'text-sm font-medium text-green-800 mb-2' },
                    '✅ Calendar Generated Successfully'
                ),
                React.createElement('div', { className: 'text-sm text-gray-700 space-y-1' },
                    React.createElement('p', null, 
                        `• ${orchestrationResult.total_campaigns} campaigns created`
                    ),
                    React.createElement('p', null, 
                        `• Expected revenue: $${orchestrationResult.expected_revenue.toLocaleString()}`
                    ),
                    orchestrationResult.dialogue_incorporated && React.createElement('p', null, 
                        '• Your notes were incorporated'
                    ),
                    orchestrationResult.ai_generated && React.createElement('p', null, 
                        '• AI-powered recommendations applied'
                    )
                ),
                React.createElement('button', {
                    onClick: () => window.location.reload(),
                    className: 'mt-3 text-sm text-blue-600 hover:text-blue-800'
                }, 'View Calendar →')
            )
        );
    }
}

// Export for use in other components
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CalendarDialogueInput;
} else {
    window.CalendarDialogueInput = CalendarDialogueInput;
}