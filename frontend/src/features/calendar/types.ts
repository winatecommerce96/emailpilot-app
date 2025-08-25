/**
 * TypeScript type definitions for EmailPilot Calendar Feature
 */

export interface Client {
  id: string;
  name: string;
  email?: string;
  phone?: string;
  company?: string;
  industry?: string;
  created_at: string;
  updated_at: string;
}

export interface CalendarEvent {
  id?: string;
  title: string;
  description?: string;
  start_date: string;
  end_date?: string;
  type: EventType;
  client_id: string;
  status: EventStatus;
  color?: string;
  recurring?: boolean;
  recurring_pattern?: RecurringPattern;
  created_at?: string;
  updated_at?: string;
}

export type EventType = 
  | 'campaign'
  | 'flow'
  | 'audit'
  | 'meeting'
  | 'deadline'
  | 'launch'
  | 'review'
  | 'planning'
  | 'other';

export type EventStatus = 
  | 'planned'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'delayed';

export interface RecurringPattern {
  frequency: 'daily' | 'weekly' | 'monthly' | 'yearly';
  interval: number;
  end_date?: string;
  count?: number;
}

export interface Goal {
  id: string;
  client_id: string;
  title: string;
  description?: string;
  target_revenue: number;
  current_revenue: number;
  target_date: string;
  status: GoalStatus;
  category: GoalCategory;
  metrics: GoalMetrics;
  created_at: string;
  updated_at: string;
}

export type GoalStatus = 
  | 'draft'
  | 'active'
  | 'completed'
  | 'paused'
  | 'cancelled';

export type GoalCategory = 
  | 'revenue'
  | 'campaigns'
  | 'flows'
  | 'segments'
  | 'subscribers'
  | 'engagement';

export interface GoalMetrics {
  progress_percentage: number;
  days_remaining: number;
  daily_target?: number;
  weekly_target?: number;
  monthly_target?: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  metadata?: {
    client_id?: string;
    context_type?: 'calendar' | 'goals' | 'campaigns';
    suggestions?: string[];
  };
}

export interface CalendarState {
  currentDate: Date;
  selectedClient: Client | null;
  events: CalendarEvent[];
  goals: Goal[];
  loading: boolean;
  error: string | null;
  showEventModal: boolean;
  selectedEvent: CalendarEvent | null;
  chatMessages: ChatMessage[];
}

export interface CalendarActions {
  setCurrentDate: (date: Date) => void;
  setSelectedClient: (client: Client | null) => void;
  loadEvents: (clientId: string, startDate?: string, endDate?: string) => Promise<void>;
  loadGoals: (clientId: string) => Promise<void>;
  createEvent: (event: Omit<CalendarEvent, 'id'>) => Promise<void>;
  updateEvent: (event: CalendarEvent) => Promise<void>;
  deleteEvent: (eventId: string) => Promise<void>;
  openEventModal: (event?: CalendarEvent) => void;
  closeEventModal: () => void;
  sendChatMessage: (message: string) => Promise<void>;
  clearChatHistory: () => void;
}

export interface FirebaseConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  storageBucket: string;
  messagingSenderId: string;
  appId: string;
}

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface CalendarViewProps {
  currentDate: Date;
  events: CalendarEvent[];
  goals: Goal[];
  selectedClient: Client | null;
  onDateChange: (date: Date) => void;
  onEventClick: (event: CalendarEvent) => void;
  onCreateEvent: (date: Date) => void;
  onDragEvent?: (eventId: string, newDate: Date) => void;
}

export interface EventModalProps {
  isOpen: boolean;
  event?: CalendarEvent;
  initialDate?: Date;
  clients: Client[];
  selectedClient?: Client;
  onSave: (event: CalendarEvent) => Promise<void>;
  onDelete?: (eventId: string) => Promise<void>;
  onClose: () => void;
}

export interface CalendarChatProps {
  messages: ChatMessage[];
  selectedClient: Client | null;
  goals: Goal[];
  events: CalendarEvent[];
  onSendMessage: (message: string) => Promise<void>;
  onClearHistory: () => void;
  isLoading?: boolean;
}

export interface DateRange {
  startDate: Date;
  endDate: Date;
}

export interface CalendarFilters {
  eventTypes?: EventType[];
  eventStatus?: EventStatus[];
  dateRange?: DateRange;
  clientIds?: string[];
}

export interface ImportedCampaign {
  id: string;
  name: string;
  type: string;
  status: string;
  scheduled_date?: string;
  launch_date?: string;
  client_name?: string;
  revenue_target?: number;
  description?: string;
}