// Enhanced AI Chat Component for Calendar with Firebase Integration
const { useState, useEffect, useRef } = React;

// Initialize services
const firebaseService = new window.FirebaseCalendarService();
const geminiService = new window.GeminiChatService(firebaseService);

function CalendarChat({ clientId, onEventAction, clientName, goals = [] }) {
    const [messages, setMessages] = useState([]);
    const [inputMessage, setInputMessage] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatHistory, setChatHistory] = useState([]);
    const [campaigns, setCampaigns] = useState({});
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
                    content: "Hello! I'm your Goal-Aware Calendar AI assistant. I can help you with questions about your campaigns, revenue goals, or make changes to your calendar. What would you like to know?",
                    timestamp: new Date()
                }
            ]);
            setChatHistory([]);
        }
    }, [clientId]);

    // Load client campaigns
    const loadCampaigns = async () => {
        try {
            const clientData = await firebaseService.getClientData(clientId);
            setCampaigns(clientData?.campaignData || {});
        } catch (error) {
            console.error('Error loading campaigns:', error);
            setCampaigns({});
        }
    };

    // Send message to AI
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
            // Send to Gemini directly
            const aiResponse = await geminiService.chatWithGemini(
                chatHistory, 
                userMessage.content, 
                clientName || 'the current client',
                campaigns,
                goals
            );

            // Remove loading message
            setMessages(prev => prev.filter(msg => msg.id !== 'loading'));

            // Try to parse as JSON action first
            try {
                const action = JSON.parse(aiResponse);
                await performAiAction(action);
            } catch (e) {
                // Not a JSON action, so it's a conversational response
                const aiMessage = {
                    id: (Date.now() + 1).toString(),
                    type: 'ai',
                    content: aiResponse,
                    timestamp: new Date()
                };

                setMessages(prev => [...prev, aiMessage]);
                chatHistory.push({ role: "model", parts: [{ text: aiResponse }] });
            }

            // Update chat history for context
            chatHistory.push({ role: "user", parts: [{ text: userMessage.content }] });
            
            // Keep only last 10 messages for context
            if (chatHistory.length > 10) {
                setChatHistory(chatHistory.slice(-10));
            }

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

    // Perform AI action (create, update, delete)
    const performAiAction = async (action) => {
        let confirmationMessage = "I'm sorry, I couldn't perform that action.";
        let actionTaken = false;

        try {
            const clientData = await firebaseService.getClientData(clientId);
            const updatedCampaigns = { ...(clientData?.campaignData || {}) };

            switch (action.action) {
                case 'delete':
                    if (updatedCampaigns[action.eventId]) {
                        delete updatedCampaigns[action.eventId];
                        actionTaken = true;
                        confirmationMessage = `Okay, I've deleted the event.`;
                    } else {
                        confirmationMessage = `I couldn't find an event with the ID ${action.eventId} to delete.`;
                    }
                    break;
                case 'update':
                    if (updatedCampaigns[action.eventId]) {
                        Object.assign(updatedCampaigns[action.eventId], action.updates);
                        actionTaken = true;
                        confirmationMessage = `Okay, I've updated the event.`;
                    } else {
                        confirmationMessage = `I couldn't find an event with the ID ${action.eventId} to update.`;
                    }
                    break;
                case 'create':
                    const newId = 'ai-event-' + Date.now();
                    const campaignType = firebaseService.detectCampaignType(action.event.title, action.event.content);
                    const CAMPAIGN_COLORS = window.CAMPAIGN_COLORS;
                    updatedCampaigns[newId] = {
                        ...action.event,
                        color: CAMPAIGN_COLORS[campaignType] || CAMPAIGN_COLORS.default
                    };
                    actionTaken = true;
                    confirmationMessage = `Okay, I've created the new event: "${action.event.title}".`;
                    break;
            }

            if (actionTaken) {
                // Save to Firebase
                await firebaseService.saveClientData(clientId, {
                    ...clientData,
                    campaignData: updatedCampaigns
                });
                
                // Update local state
                setCampaigns(updatedCampaigns);
                
                // Trigger calendar refresh
                if (onEventAction) {
                    onEventAction();
                }
            }
        } catch (error) {
            console.error('Error performing AI action:', error);
            confirmationMessage = "I encountered an error while trying to perform that action.";
        }

        // Add confirmation message to chat
        const aiBubble = {
            id: Date.now().toString(),
            type: 'ai',
            content: confirmationMessage,
            isAction: actionTaken,
            timestamp: new Date()
        };

        setMessages(prev => [...prev, aiBubble]);
        chatHistory.push({ role: "model", parts: [{ text: confirmationMessage }] });
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

    return (
        <div className="bg-white rounded-xl shadow-lg">
            {/* Chat Header */}
            <div className="p-4 border-b border-gray-200">
                <div className="flex justify-between items-center">
                    <h3 className="text-lg font-semibold text-gray-900">
                        Calendar AI Assistant
                    </h3>
                    <button
                        onClick={handleClearChat}
                        className="text-sm text-gray-500 hover:text-gray-700"
                    >
                        Clear Chat
                    </button>
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
                            text="How many campaigns this month?"
                            onClick={() => setInputMessage("How many campaigns do we have scheduled for this month?")}
                        />
                        <QuickActionButton
                            text="What's next week's schedule?"
                            onClick={() => setInputMessage("What campaigns are scheduled for next week?")}
                        />
                        <QuickActionButton
                            text="Show SMS campaigns"
                            onClick={() => setInputMessage("Show me all SMS Alert campaigns")}
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
    const isError = message.isError;
    const isAction = message.isAction;

    return (
        <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-xs lg:max-w-md px-3 py-2 rounded-lg ${
                isUser 
                    ? 'bg-indigo-600 text-white' 
                    : isError 
                    ? 'bg-red-100 text-red-800 border border-red-200'
                    : isAction
                    ? 'bg-green-100 text-green-800 border border-green-200'
                    : 'bg-gray-200 text-gray-800'
            }`}>
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                
                {isAction && message.actionType && (
                    <div className="mt-1 text-xs opacity-75">
                        Action: {message.actionType}
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

// Example usage suggestions component
function ChatSuggestions() {
    return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mt-3">
            <h4 className="font-medium text-blue-900 text-sm mb-2">Try asking:</h4>
            <ul className="text-sm text-blue-800 space-y-1">
                <li>• "How many campaigns are scheduled for October?"</li>
                <li>• "Show me all nurturing campaigns"</li>
                <li>• "Delete the cheese club campaign on October 15th"</li>
                <li>• "Create a new SMS campaign for next Friday"</li>
                <li>• "Move the promotion campaign to next week"</li>
            </ul>
        </div>
    );
}

// Make CalendarChat available globally
window.CalendarChat = CalendarChat;