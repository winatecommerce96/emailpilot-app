/**
 * AI Service for EmailPilot Calendar Chat
 * Provides server-proxied AI interactions for campaign planning assistance
 */

import { ChatMessage, Client, Goal, CalendarEvent, APIResponse } from '../types';

class AIService {
  private baseUrl: string;
  private initialized: boolean = false;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
  }

  /**
   * Initialize the AI service
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/chat/status', 'GET');
      if (!response.ok) {
        throw new Error('AI Chat API not available');
      }
      this.initialized = true;
    } catch (error) {
      console.warn('AI Chat API connection failed:', error);
      this.initialized = true; // Continue in fallback mode
    }
  }

  /**
   * Generic HTTP request helper
   */
  private async makeRequest(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    data?: any
  ): Promise<Response> {
    const url = `${this.baseUrl}${endpoint}`;
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      credentials: 'include',
    };

    if (data && method !== 'GET') {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response;
  }

  /**
   * Send a chat message and get AI response
   */
  async sendMessage(
    message: string,
    context: {
      client?: Client;
      goals?: Goal[];
      events?: CalendarEvent[];
      chatHistory?: ChatMessage[];
    }
  ): Promise<ChatMessage> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/chat', 'POST', {
        message,
        context: {
          client_id: context.client?.id,
          client_name: context.client?.name,
          client_industry: context.client?.industry,
          goals: context.goals?.map(g => ({
            id: g.id,
            title: g.title,
            target_revenue: g.target_revenue,
            current_revenue: g.current_revenue,
            target_date: g.target_date,
            progress: g.metrics.progress_percentage,
            status: g.status
          })),
          events: context.events?.map(e => ({
            id: e.id,
            title: e.title,
            type: e.type,
            start_date: e.start_date,
            status: e.status
          })),
          recent_messages: context.chatHistory?.slice(-5).map(m => ({
            role: m.role,
            content: m.content
          }))
        }
      });

      const data: APIResponse<{ response: string; suggestions?: string[] }> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to get AI response');
      }

      const aiResponse = data.data!;
      
      return {
        id: this.generateMessageId(),
        role: 'assistant',
        content: aiResponse.response,
        timestamp: new Date().toISOString(),
        metadata: {
          client_id: context.client?.id,
          context_type: 'calendar',
          suggestions: aiResponse.suggestions
        }
      };
    } catch (error) {
      console.error('Failed to send chat message:', error);
      
      // Return fallback response
      return {
        id: this.generateMessageId(),
        role: 'assistant',
        content: 'I apologize, but I\'m having trouble connecting to the AI service right now. Please try again later.',
        timestamp: new Date().toISOString(),
        metadata: {
          client_id: context.client?.id,
          context_type: 'calendar'
        }
      };
    }
  }

  /**
   * Get campaign planning suggestions
   */
  async getCampaignSuggestions(
    client: Client,
    goals: Goal[],
    timeframe?: { start: string; end: string }
  ): Promise<{
    campaigns: Array<{
      title: string;
      type: string;
      description: string;
      suggestedDate: string;
      expectedRevenue: number;
    }>;
    insights: string[];
  }> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/campaign-suggestions', 'POST', {
        client: {
          id: client.id,
          name: client.name,
          industry: client.industry
        },
        goals: goals.map(g => ({
          title: g.title,
          target_revenue: g.target_revenue,
          current_revenue: g.current_revenue,
          target_date: g.target_date,
          progress: g.metrics.progress_percentage
        })),
        timeframe
      });

      const data: APIResponse<{
        campaigns: Array<{
          title: string;
          type: string;
          description: string;
          suggestedDate: string;
          expectedRevenue: number;
        }>;
        insights: string[];
      }> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to get campaign suggestions');
      }

      return data.data!;
    } catch (error) {
      console.error('Failed to get campaign suggestions:', error);
      
      // Return fallback suggestions
      return this.getFallbackSuggestions(client, goals);
    }
  }

  /**
   * Get chat history for a client
   */
  async getChatHistory(clientId: string, limit: number = 50): Promise<ChatMessage[]> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/firebase_calendar/chat/history/${clientId}?limit=${limit}`, 'GET');
      const data: APIResponse<ChatMessage[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to get chat history');
      }

      return data.data || [];
    } catch (error) {
      console.error('Failed to get chat history:', error);
      return this.getFallbackChatHistory(clientId);
    }
  }

  /**
   * Clear chat history for a client
   */
  async clearChatHistory(clientId: string): Promise<void> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/firebase_calendar/chat/history/${clientId}`, 'DELETE');
      const data: APIResponse<void> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to clear chat history');
      }

      // Clear local fallback data too
      localStorage.removeItem(`emailpilot_chat_${clientId}`);
    } catch (error) {
      console.error('Failed to clear chat history:', error);
      throw error;
    }
  }

  /**
   * Get AI insights about goals progress
   */
  async getGoalsInsights(
    client: Client,
    goals: Goal[]
  ): Promise<{
    summary: string;
    recommendations: string[];
    risksAndOpportunities: string[];
  }> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/firebase_calendar/goals-insights', 'POST', {
        client: {
          id: client.id,
          name: client.name,
          industry: client.industry
        },
        goals: goals.map(g => ({
          title: g.title,
          target_revenue: g.target_revenue,
          current_revenue: g.current_revenue,
          target_date: g.target_date,
          progress: g.metrics.progress_percentage,
          days_remaining: g.metrics.days_remaining,
          status: g.status
        }))
      });

      const data: APIResponse<{
        summary: string;
        recommendations: string[];
        risksAndOpportunities: string[];
      }> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to get goals insights');
      }

      return data.data!;
    } catch (error) {
      console.error('Failed to get goals insights:', error);
      
      // Return basic fallback insights
      return this.getFallbackGoalsInsights(goals);
    }
  }

  /**
   * Generate message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get fallback campaign suggestions
   */
  private getFallbackSuggestions(client: Client, goals: Goal[]): {
    campaigns: Array<{
      title: string;
      type: string;
      description: string;
      suggestedDate: string;
      expectedRevenue: number;
    }>;
    insights: string[];
  } {
    const activeGoals = goals.filter(g => g.status === 'active');
    const totalTargetRevenue = activeGoals.reduce((sum, g) => g.target_revenue, 0);
    
    return {
      campaigns: [
        {
          title: `Welcome Series for ${client.name}`,
          type: 'flow',
          description: 'Automated welcome sequence for new subscribers',
          suggestedDate: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          expectedRevenue: totalTargetRevenue * 0.15
        },
        {
          title: `Monthly Newsletter - ${new Date().toLocaleString('default', { month: 'long' })}`,
          type: 'campaign',
          description: 'Monthly engagement and product updates',
          suggestedDate: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
          expectedRevenue: totalTargetRevenue * 0.08
        }
      ],
      insights: [
        `Focus on building a strong welcome series to capture early revenue from ${client.name}'s new subscribers.`,
        'Consider seasonal campaigns to boost engagement and sales.',
        `With ${activeGoals.length} active goals, prioritize campaigns that support multiple objectives.`
      ]
    };
  }

  /**
   * Get fallback chat history from localStorage
   */
  private getFallbackChatHistory(clientId: string): ChatMessage[] {
    const fallbackData = localStorage.getItem(`emailpilot_chat_${clientId}`);
    if (fallbackData) {
      try {
        return JSON.parse(fallbackData);
      } catch (error) {
        console.warn('Failed to parse fallback chat history');
      }
    }
    return [];
  }

  /**
   * Save chat message to localStorage fallback
   */
  saveChatMessage(clientId: string, message: ChatMessage): void {
    try {
      const history = this.getFallbackChatHistory(clientId);
      history.push(message);
      
      // Keep only last 100 messages
      const trimmedHistory = history.slice(-100);
      
      localStorage.setItem(`emailpilot_chat_${clientId}`, JSON.stringify(trimmedHistory));
    } catch (error) {
      console.warn('Failed to save chat message to fallback:', error);
    }
  }

  /**
   * Get fallback goals insights
   */
  private getFallbackGoalsInsights(goals: Goal[]): {
    summary: string;
    recommendations: string[];
    risksAndOpportunities: string[];
  } {
    const activeGoals = goals.filter(g => g.status === 'active');
    const completedGoals = goals.filter(g => g.status === 'completed');
    const averageProgress = activeGoals.length > 0 
      ? activeGoals.reduce((sum, g) => sum + g.metrics.progress_percentage, 0) / activeGoals.length
      : 0;

    return {
      summary: `You have ${activeGoals.length} active goals with an average progress of ${averageProgress.toFixed(1)}%. ${completedGoals.length} goals have been completed.`,
      recommendations: [
        averageProgress < 50 ? 'Consider increasing campaign frequency to boost revenue' : 'You\'re making good progress on your goals',
        'Focus on high-impact campaigns during peak seasons',
        'Review goal timelines and adjust targets if needed'
      ],
      risksAndOpportunities: [
        activeGoals.some(g => g.metrics.days_remaining < 30 && g.metrics.progress_percentage < 70) 
          ? 'Some goals may be at risk of missing targets' 
          : 'Goals appear to be on track',
        'Opportunity to leverage successful campaigns for similar clients',
        'Consider A/B testing different campaign approaches'
      ]
    };
  }

  /**
   * Check if service is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const aiService = new AIService();
export default aiService;