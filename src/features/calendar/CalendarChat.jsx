/**
 * CalendarChat Component for EmailPilot
 * AI-powered chat interface for campaign planning assistance
 */

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { CalendarChatProps } from './types';
import aiService from './services/ai';

const CalendarChat = ({
  messages,
  selectedClient,
  goals,
  events,
  onSendMessage,
  onClearHistory,
  isLoading = false
}) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Get smart suggestions based on current context
  const smartSuggestions = useMemo(() => {
    if (!selectedClient) {
      return [
        "Help me plan a marketing calendar",
        "What are the best campaign types for email marketing?",
        "How do I set up automated flows?"
      ];
    }

    const suggestions = [
      `Create a campaign calendar for ${selectedClient.name}`,
      "What campaigns should I prioritize this month?",
      "Help me optimize my email marketing strategy"
    ];

    // Add goal-specific suggestions
    if (goals.length > 0) {
      const activeGoals = goals.filter(g => g.status === 'active');
      if (activeGoals.length > 0) {
        suggestions.push(`How can I achieve my revenue goals of $${activeGoals.reduce((sum, g) => sum + g.target_revenue, 0).toLocaleString()}?`);
      }
      
      const behindGoals = activeGoals.filter(g => g.metrics.progress_percentage < 50);
      if (behindGoals.length > 0) {
        suggestions.push("What campaigns can help me catch up on my goals?");
      }
    }

    // Add event-specific suggestions
    const upcomingEvents = events.filter(e => {
      const eventDate = new Date(e.start_date);
      const today = new Date();
      const diffDays = (eventDate - today) / (1000 * 60 * 60 * 24);
      return diffDays >= 0 && diffDays <= 30 && e.status === 'planned';
    });

    if (upcomingEvents.length > 0) {
      suggestions.push(`I have ${upcomingEvents.length} events coming up. Any preparation tips?`);
    }

    // Industry-specific suggestions
    if (selectedClient.industry) {
      suggestions.push(`Best email practices for ${selectedClient.industry} industry`);
    }

    return suggestions.slice(0, 6); // Limit to 6 suggestions
  }, [selectedClient, goals, events]);

  // Handle message submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || isLoading) return;

    const message = inputMessage.trim();
    setInputMessage('');
    setShowSuggestions(false);
    
    try {
      await onSendMessage(message);
    } catch (error) {
      console.error('Failed to send message:', error);
    }
  };

  // Handle suggestion click
  const handleSuggestionClick = async (suggestion) => {
    setInputMessage(suggestion);
    setShowSuggestions(false);
    
    try {
      await onSendMessage(suggestion);
    } catch (error) {
      console.error('Failed to send suggestion:', error);
    }
  };

  // Handle clear history
  const handleClearHistory = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      onClearHistory();
      setShowSuggestions(true);
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffHours = (now - date) / (1000 * 60 * 60);
    
    if (diffHours < 1) {
      return 'Just now';
    } else if (diffHours < 24) {
      return `${Math.floor(diffHours)} hours ago`;
    } else {
      return date.toLocaleDateString();
    }
  };

  // Parse message content for better display
  const parseMessageContent = (content) => {
    // Simple markdown-like parsing for better formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
      .replace(/\n/g, '<br>');
  };

  const isEmpty = messages.length === 0;

  return (
    <div className={`bg-white rounded-lg shadow-lg transition-all duration-300 ${
      isExpanded ? 'h-[600px]' : 'h-[400px]'
    }`}>
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-200 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-white bg-opacity-20 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-semibold">AI Campaign Assistant</h3>
              <p className="text-sm text-blue-100">
                {selectedClient ? `Planning for ${selectedClient.name}` : 'Ready to help with your campaigns'}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1 hover:bg-white hover:bg-opacity-20 rounded"
              title={isExpanded ? 'Minimize' : 'Expand'}
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
                  d={isExpanded ? "M19 14l-7-7-7 7" : "M5 10l7-7 7 7"} />
              </svg>
            </button>
            {messages.length > 0 && (
              <button
                onClick={handleClearHistory}
                className="p-1 hover:bg-white hover:bg-opacity-20 rounded"
                title="Clear History"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4" style={{ height: isExpanded ? '460px' : '260px' }}>
        {isEmpty && (
          <div className="text-center py-8">
            <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            </div>
            <h4 className="text-lg font-medium text-gray-800 mb-2">Welcome to AI Campaign Assistant</h4>
            <p className="text-gray-600 mb-6">
              I'm here to help you plan effective email campaigns and achieve your revenue goals.
              {selectedClient && ` Let's create a winning strategy for ${selectedClient.name}!`}
            </p>

            {/* Smart Suggestions */}
            {showSuggestions && (
              <div>
                <p className="text-sm text-gray-500 mb-3">Try asking me about:</p>
                <div className="grid grid-cols-1 gap-2">
                  {smartSuggestions.map((suggestion, index) => (
                    <button
                      key={index}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="text-left text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg p-3 transition-colors duration-200"
                      disabled={isLoading}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Chat Messages */}
        {messages.map((message) => (
          <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${message.role === 'user' ? 'order-2' : 'order-1'}`}>
              <div className={`
                p-3 rounded-lg shadow-sm
                ${message.role === 'user' 
                  ? 'bg-blue-600 text-white ml-4' 
                  : 'bg-gray-100 text-gray-800 mr-4'
                }
              `}>
                <div 
                  className="text-sm"
                  dangerouslySetInnerHTML={{ __html: parseMessageContent(message.content) }}
                />
                
                {/* Suggestions from AI */}
                {message.role === 'assistant' && message.metadata?.suggestions && (
                  <div className="mt-3 space-y-1">
                    <p className="text-xs font-medium text-gray-600">Quick follow-ups:</p>
                    {message.metadata.suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="block text-xs bg-white bg-opacity-20 hover:bg-opacity-30 rounded px-2 py-1 transition-colors duration-200"
                        disabled={isLoading}
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
              </div>
              
              <div className={`text-xs text-gray-500 mt-1 ${
                message.role === 'user' ? 'text-right' : 'text-left'
              }`}>
                {formatTimestamp(message.timestamp)}
              </div>
            </div>
          </div>
        ))}

        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 p-3 rounded-lg mr-4 shadow-sm">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
                <span className="text-sm">AI is thinking...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200">
        <form onSubmit={handleSubmit} className="flex space-x-3">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder={selectedClient 
                ? `Ask me about campaigns for ${selectedClient.name}...` 
                : "Ask me about email marketing strategies..."
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
              disabled={isLoading}
            />
          </div>
          
          <button
            type="submit"
            disabled={isLoading || !inputMessage.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </form>

        {/* Context indicator */}
        {selectedClient && (
          <div className="mt-2 text-xs text-gray-500 flex items-center space-x-2">
            <div className="w-2 h-2 bg-green-400 rounded-full"></div>
            <span>
              Context: {selectedClient.name}
              {goals.length > 0 && ` • ${goals.length} goals`}
              {events.length > 0 && ` • ${events.length} events`}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export default CalendarChat;