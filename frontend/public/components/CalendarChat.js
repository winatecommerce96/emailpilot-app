// Enhanced AI Chat Component for Calendar with FastAPI Backend Integration
const { useState, useEffect, useRef } = React;

function CalendarChat({ clientId, onEventAction, clientName, goals = [] }) {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatHistory, setChatHistory] = useState([]);
    const [campaigns, setCampaigns] = useState({});
    const [lastActionId, setLastActionId] = useState(null);
    const messagesEndRef = useRef(null);
    
    // Auto-scroll to bottom when new messages are added
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Load campaigns and reset chat when client changes
    useEffect(() => {
        if (clientId) {
            loadCampaigns();
            setMessages([
                {
                    id: 'welcome',
                    type: 'ai',
                    content: "Hello! I'm your enhanced Calendar AI assistant. I can help you query calendar events, add new events, update existing ones, or delete events through natural language. Try asking me about your campaigns or tell me to create/modify events!",
                    timestamp: new Date()
                }
            ]);
            setChatHistory([]);
        }
    }, [clientId]);

    // Load client campaigns from API
    const loadCampaigns = async () => {
        try {
            const response = await fetch(`/api/calendar/events/${clientId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const events = await response.json();
                setCampaigns(events || {});
            } else {
                console.error('Failed to load campaigns:', response.statusText);
                setCampaigns({});
            }
        } catch (error) {
            console.error('Error loading campaigns:', error);
            setCampaigns({});
        }
    };

    // Send message to AI using enhanced backend endpoint
    const handleSendMessage = async () => {
        if (!inputMessage.trim() || !clientId || isLoading) return;

        const userMessage = {
            id: Date.now().toString(),
            type: 'user',
            content: inputMessage.trim(),
            timestamp: new Date()
        };

        // Add user message to chat
        setMessages(prev => [...prev, userMessage]);
        setInputMessage('');
        setIsLoading(true);

        // Add loading indicator
        const loadingMessage = {
            id: 'loading',
            type: 'ai',
            content: '',
            isLoading: true,
            timestamp: new Date()
        };
        setMessages(prev => [...prev, loadingMessage]);

        try {
            // Send to enhanced chat endpoint
            const response = await fetch('/api/calendar/ai/chat-enhanced', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: userMessage.content,
                    client_id: clientId,
                    client_name: clientName || 'the current client',
                    chat_history: chatHistory,
                    goals: goals
                })
            });

            // Remove loading message
            setMessages(prev => prev.filter(msg => msg.id !== 'loading'));

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Create AI message
            const aiMessage = {
                id: (Date.now() + 1).toString(),
                type: 'ai',
                content: data.response,
                timestamp: new Date(),
                isAction: data.is_action || false,
                actionType: data.action_type || null,
                actionExecuted: data.action_executed || false
            };

            setMessages(prev => [...prev, aiMessage]);

            // If an action was executed, refresh the calendar
            if (data.action_executed) {
                await loadCampaigns(); // Refresh campaigns data
                if (onEventAction) {
                    onEventAction(); // Trigger calendar refresh
                }
                
                // Show success feedback
                const successMessage = {
                    id: (Date.now() + 2).toString(),
                    type: 'system',
                    content: `✅ Calendar updated! ${getActionFeedback(data.action_type)}`,
                    timestamp: new Date(),
                    isSuccess: true
                };
                
                setTimeout(() => {
                    setMessages(prev => [...prev, successMessage]);
                }, 500);
            }

            // Update chat history for context (keep format simple)
            const newHistory = [
                ...chatHistory,
                { role: "user", content: userMessage.content },
                { role: "assistant", content: data.response }
            ];
            
            // Keep only last 10 messages for context
            setChatHistory(newHistory.slice(-10));

        } catch (error) {
            // Remove loading message
            setMessages(prev => prev.filter(msg => msg.id !== 'loading'));
            
            const errorMessage = {
                id: (Date.now() + 1).toString(),
                type: 'ai',
                content: "I'm sorry, I encountered an error processing your request. Please try again.",
                isError: true,
                timestamp: new Date()
            };

            setMessages(prev => [...prev, errorMessage]);
            console.error('Chat error:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Get feedback message for action types
    const getActionFeedback = (actionType) => {
        switch (actionType) {
            case 'create': return 'New event added to calendar';
            case 'update': return 'Event updated successfully';
            case 'delete': return 'Event removed from calendar';
            default: return 'Action completed';
        }
    };


    // Handle Enter key press
    const handleKeyPress = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSendMessage();
        }
    };

    // Clear chat
    const handleClearChat = () => {
        setMessages([
            {
                id: 'welcome',
                type: 'ai',
                content: "Chat cleared! How can I help you with your calendar?",
                timestamp: new Date()
            }
        ]);
        setChatHistory([]);
    };

    // Show suggestions
    const handleShowSuggestions = () => {
        const suggestionMessage = {
            id: Date.now().toString(),
            type: 'ai',
            content: "Here are some things you can ask me to do:\n\n🔍 **Query Events:**\n• Show me all campaigns for this month\n• What events are scheduled for next week?\n• Find all SMS campaigns in December\n\n➕ **Create Events:**\n• Create a Black Friday sale campaign on November 24th\n• Add a nurturing email series starting tomorrow\n• Schedule a product launch event for next Friday at 2pm\n\n✏️ **Update/Delete:**\n• Move the holiday campaign to December 15th\n• Change the title of tomorrow's email to 'Special Offer'\n• Delete all cancelled campaigns\n\nJust tell me what you want to do in plain English!",
            timestamp: new Date(),
            isSuggestion: true
        };
        setMessages(prev => [...prev, suggestionMessage]);
    };

    return (
        <div className="bg-white rounded-xl shadow-lg">
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900">
                        Enhanced Calendar AI
                    </h3>
                    <div className="flex space-x-2">
                        <button
                            onClick={handleShowSuggestions}
                            className="text-sm text-blue-600 hover:text-blue-800"
                        >
                            Help
                        </button>
                        <button
                            onClick={handleClearChat}
                            className="text-sm text-gray-500 hover:text-gray-700"
                        >
                            Clear
                        </button>
                    </div>
                </div>
                {!clientId && (
                    <p className="text-sm text-yellow-600 mt-1">
                        Please select a client to start chatting about their calendar.
                    </p>
                )}
            </div>

            {/* Messages Container */}
            <div className="h-64 overflow-y-auto p-4 bg-gray-50">
                <div className="space-y-3">
                    {messages.map(message => (
                        <ChatMessage key={message.id} message={message} />
                    ))}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200">
                <div className="flex space-x-2">
                    <input
                        type="text"
                        value={inputMessage}
                        onChange={(e) => setInputMessage(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder={
                            clientId 
                                ? "Ask about campaigns or request changes..." 
                                : "Select a client first..."
                        }
                        disabled={!clientId || isLoading}
                        className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
                    />
                    <button
                        onClick={handleSendMessage}
                        disabled={!clientId || !inputMessage.trim() || isLoading}
                        className="px-4 py-2 bg-indigo-600 text-white font-medium rounded-md hover:bg-indigo-700 disabled:bg-indigo-300 disabled:cursor-not-allowed"
                    >
                        {isLoading ? 'Sending...' : 'Send'}
                    </button>
                </div>
                
                {/* Quick Action Buttons */}
                {clientId && (
                    <div className="mt-2 flex flex-wrap gap-2">
                        <QuickActionButton
                            text="Show upcoming events"
                            onClick={() => setInputMessage("Show me all upcoming calendar events")}
                        />
                        <QuickActionButton
                            text="Create new campaign"
                            onClick={() => setInputMessage("Create a new email campaign for next Friday")}
                        />
                        <QuickActionButton
                            text="What's this week?"
                            onClick={() => setInputMessage("What campaigns are scheduled for this week?")}
                        />
                        <QuickActionButton
                            text="Delete old events"
                            onClick={() => setInputMessage("Delete any events older than 30 days")}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}

// Chat Message Component
function ChatMessage({ message }) {
    if (message.isLoading) {
        return (
            <div className="flex justify-start">
                <div className="bg-gray-200 rounded-lg px-3 py-2 max-w-xs">
                    <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                        <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                    </div>
                </div>
            </div>
        );
    }

    const isUser = message.type === 'user';
    const isSystem = message.type === 'system';
    const isError = message.isError;
    const isAction = message.isAction;
    const isSuccess = message.isSuccess;
    const isSuggestion = message.isSuggestion;
    const actionExecuted = message.actionExecuted;

    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                isUser 
                    ? 'bg-indigo-600 text-white' 
                    : isSystem && isSuccess
                    ? 'bg-green-50 text-green-800 border border-green-200'
                    : isError 
                    ? 'bg-red-100 text-red-800 border border-red-200'
                    : isSuggestion
                    ? 'bg-blue-50 text-blue-900 border border-blue-300'
                    : isAction || actionExecuted
                    ? 'bg-blue-50 text-blue-800 border border-blue-200'
                    : 'bg-gray-200 text-gray-800'
            }`}>
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                
                {(isAction || actionExecuted) && message.actionType && (
                    <div className="mt-1 text-xs opacity-75">
                        {actionExecuted ? `✓ Action Completed: ${message.actionType}` : `Action: ${message.actionType}`}
                    </div>
                )}
                
                <div className={`text-xs mt-1 opacity-75 ${
                    isUser ? 'text-indigo-200' : 'text-gray-500'
                }`}>
                    {message.timestamp.toLocaleTimeString([], { 
                        hour: '2-digit', 
                        minute: '2-digit' 
                    })}
                </div>
            </div>
        </div>
    );
}

// Quick Action Button Component
function QuickActionButton({ text, onClick }) {
    return (
        <button
            onClick={onClick}
            className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-full hover:bg-gray-200 transition-colors"
        >
            {text}
        </button>
    );
}

// Enhanced usage suggestions component
function ChatSuggestions() {
    return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-3">
            <h4 className="font-medium text-blue-900 text-sm mb-2">Enhanced AI Assistant - Try asking:</h4>
            <div className="text-sm text-blue-800 space-y-2">
                <div>
                    <strong>Query Events:</strong>
                    <ul className="ml-2 space-y-1">
                        <li>• "Show me all campaigns for this month"</li>
                        <li>• "What events are scheduled for next week?"</li>
                        <li>• "Find all SMS campaigns in December"</li>
                    </ul>
                </div>
                <div>
                    <strong>Create Events:</strong>
                    <ul className="ml-2 space-y-1">
                        <li>• "Create a Black Friday sale campaign on November 24th"</li>
                        <li>• "Add a nurturing email series starting tomorrow"</li>
                        <li>• "Schedule a product launch event for next Friday at 2pm"</li>
                    </ul>
                </div>
                <div>
                    <strong>Update/Delete:</strong>
                    <ul className="ml-2 space-y-1">
                        <li>• "Move the holiday campaign to December 15th"</li>
                        <li>• "Change the title of tomorrow's email to 'Special Offer'"</li>
                        <li>• "Delete all cancelled campaigns"</li>
                    </ul>
                </div>
            </div>
        </div>
    );
}

// Make CalendarChat available globally
window.CalendarChat = CalendarChat;