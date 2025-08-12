/**
 * Goals Service for EmailPilot Calendar
 * Handles revenue goals and performance tracking
 */

import { Goal, Client, APIResponse } from '../types';

class GoalsService {
  private baseUrl: string;
  private initialized: boolean = false;

  constructor() {
    this.baseUrl = process.env.REACT_APP_API_BASE_URL || window.location.origin;
  }

  /**
   * Initialize the goals service
   */
  async initialize(): Promise<void> {
    if (this.initialized) return;
    
    try {
      const response = await this.makeRequest('/api/goals/status', 'GET');
      if (!response.ok) {
        throw new Error('Goals API not available');
      }
      this.initialized = true;
    } catch (error) {
      console.warn('Goals API connection failed:', error);
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
   * Get goals for a specific client
   */
  async getClientGoals(clientId: string): Promise<Goal[]> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/goals/client/${clientId}`, 'GET');
      const data: APIResponse<Goal[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch client goals');
      }
      
      const goals = data.data || [];
      
      // Calculate metrics for each goal
      return goals.map(goal => ({
        ...goal,
        metrics: this.calculateGoalMetrics(goal)
      }));
    } catch (error) {
      console.error('Failed to fetch client goals:', error);
      return this.getFallbackGoals(clientId);
    }
  }

  /**
   * Get all goals across all clients
   */
  async getAllGoals(): Promise<Goal[]> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/goals/all', 'GET');
      const data: APIResponse<Goal[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to fetch all goals');
      }
      
      const goals = data.data || [];
      
      return goals.map(goal => ({
        ...goal,
        metrics: this.calculateGoalMetrics(goal)
      }));
    } catch (error) {
      console.error('Failed to fetch all goals:', error);
      return [];
    }
  }

  /**
   * Create a new goal
   */
  async createGoal(goal: Omit<Goal, 'id' | 'created_at' | 'updated_at' | 'metrics'>): Promise<Goal> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/goals', 'POST', goal);
      const data: APIResponse<Goal> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to create goal');
      }
      
      const createdGoal = data.data!;
      return {
        ...createdGoal,
        metrics: this.calculateGoalMetrics(createdGoal)
      };
    } catch (error) {
      console.error('Failed to create goal:', error);
      throw error;
    }
  }

  /**
   * Update an existing goal
   */
  async updateGoal(goal: Goal): Promise<Goal> {
    await this.initialize();
    
    if (!goal.id) {
      throw new Error('Goal ID is required for updates');
    }

    try {
      const response = await this.makeRequest(`/api/goals/${goal.id}`, 'PUT', goal);
      const data: APIResponse<Goal> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to update goal');
      }
      
      const updatedGoal = data.data!;
      return {
        ...updatedGoal,
        metrics: this.calculateGoalMetrics(updatedGoal)
      };
    } catch (error) {
      console.error('Failed to update goal:', error);
      throw error;
    }
  }

  /**
   * Delete a goal
   */
  async deleteGoal(goalId: string): Promise<void> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/goals/${goalId}`, 'DELETE');
      const data: APIResponse<void> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to delete goal');
      }
    } catch (error) {
      console.error('Failed to delete goal:', error);
      throw error;
    }
  }

  /**
   * Update goal progress with current revenue
   */
  async updateGoalProgress(goalId: string, currentRevenue: number): Promise<Goal> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest(`/api/goals/${goalId}/progress`, 'PUT', {
        current_revenue: currentRevenue
      });
      const data: APIResponse<Goal> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to update goal progress');
      }
      
      const updatedGoal = data.data!;
      return {
        ...updatedGoal,
        metrics: this.calculateGoalMetrics(updatedGoal)
      };
    } catch (error) {
      console.error('Failed to update goal progress:', error);
      throw error;
    }
  }

  /**
   * Generate goals for a client using AI
   */
  async generateGoals(
    clientId: string,
    context?: {
      industry?: string;
      currentRevenue?: number;
      targetGrowth?: number;
      timeframe?: number; // months
    }
  ): Promise<Goal[]> {
    await this.initialize();
    
    try {
      const response = await this.makeRequest('/api/goals/generate', 'POST', {
        client_id: clientId,
        context
      });
      const data: APIResponse<Goal[]> = await response.json();
      
      if (!data.success) {
        throw new Error(data.error || 'Failed to generate goals');
      }
      
      const goals = data.data || [];
      
      return goals.map(goal => ({
        ...goal,
        metrics: this.calculateGoalMetrics(goal)
      }));
    } catch (error) {
      console.error('Failed to generate goals:', error);
      throw error;
    }
  }

  /**
   * Get goals summary for dashboard
   */
  async getGoalsSummary(clientId?: string): Promise<{
    totalGoals: number;
    activeGoals: number;
    completedGoals: number;
    totalTargetRevenue: number;
    totalCurrentRevenue: number;
    averageProgress: number;
    goalsOnTrack: number;
    goalsBehind: number;
  }> {
    const goals = clientId ? await this.getClientGoals(clientId) : await this.getAllGoals();
    
    const activeGoals = goals.filter(g => g.status === 'active');
    const completedGoals = goals.filter(g => g.status === 'completed');
    const goalsOnTrack = goals.filter(g => 
      g.metrics.progress_percentage >= this.calculateExpectedProgress(g)
    );
    const goalsBehind = goals.filter(g => 
      g.metrics.progress_percentage < this.calculateExpectedProgress(g) && g.status === 'active'
    );

    const totalTargetRevenue = goals.reduce((sum, g) => sum + g.target_revenue, 0);
    const totalCurrentRevenue = goals.reduce((sum, g) => sum + g.current_revenue, 0);
    const averageProgress = goals.length > 0 
      ? goals.reduce((sum, g) => sum + g.metrics.progress_percentage, 0) / goals.length
      : 0;

    return {
      totalGoals: goals.length,
      activeGoals: activeGoals.length,
      completedGoals: completedGoals.length,
      totalTargetRevenue,
      totalCurrentRevenue,
      averageProgress,
      goalsOnTrack: goalsOnTrack.length,
      goalsBehind: goalsBehind.length,
    };
  }

  /**
   * Calculate goal metrics
   */
  private calculateGoalMetrics(goal: Goal): Goal['metrics'] {
    const progress_percentage = goal.target_revenue > 0 
      ? Math.min(100, (goal.current_revenue / goal.target_revenue) * 100)
      : 0;

    const targetDate = new Date(goal.target_date);
    const now = new Date();
    const days_remaining = Math.max(0, Math.ceil((targetDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24)));
    
    const remaining_revenue = Math.max(0, goal.target_revenue - goal.current_revenue);
    const daily_target = days_remaining > 0 ? remaining_revenue / days_remaining : 0;
    const weekly_target = daily_target * 7;
    const monthly_target = daily_target * 30;

    return {
      progress_percentage: Math.round(progress_percentage * 100) / 100,
      days_remaining,
      daily_target: Math.round(daily_target * 100) / 100,
      weekly_target: Math.round(weekly_target * 100) / 100,
      monthly_target: Math.round(monthly_target * 100) / 100,
    };
  }

  /**
   * Calculate expected progress based on time elapsed
   */
  private calculateExpectedProgress(goal: Goal): number {
    const createdDate = new Date(goal.created_at);
    const targetDate = new Date(goal.target_date);
    const now = new Date();

    const totalDays = (targetDate.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24);
    const elapsedDays = (now.getTime() - createdDate.getTime()) / (1000 * 60 * 60 * 24);

    if (totalDays <= 0 || elapsedDays <= 0) return 0;
    if (elapsedDays >= totalDays) return 100;

    return (elapsedDays / totalDays) * 100;
  }

  /**
   * Get fallback goals from localStorage
   */
  private getFallbackGoals(clientId: string): Goal[] {
    const fallbackData = localStorage.getItem(`emailpilot_goals_${clientId}`);
    if (fallbackData) {
      try {
        const goals = JSON.parse(fallbackData);
        return goals.map((goal: Goal) => ({
          ...goal,
          metrics: this.calculateGoalMetrics(goal)
        }));
      } catch (error) {
        console.warn('Failed to parse fallback goals data');
      }
    }
    return [];
  }

  /**
   * Save goals to localStorage as fallback
   */
  private saveFallbackGoals(clientId: string, goals: Goal[]): void {
    try {
      localStorage.setItem(`emailpilot_goals_${clientId}`, JSON.stringify(goals));
    } catch (error) {
      console.warn('Failed to save fallback goals:', error);
    }
  }

  /**
   * Check if service is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const goalsService = new GoalsService();
export default goalsService;