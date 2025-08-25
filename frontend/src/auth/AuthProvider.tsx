import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import axios from 'axios';
import { getDebugBus } from '@debug/debugBus';

interface User {
  id: string;
  email: string;
  name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signOut: () => Promise<void>;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  signIn: async () => ({ success: false }),
  signOut: async () => {},
  isAuthenticated: false
});

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

interface Props {
  children: ReactNode;
}

export function AuthProvider({ children }: Props) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Configure axios defaults
  useEffect(() => {
    // Set base URL
    axios.defaults.baseURL = window.location.origin;
    
    // Add request interceptor to add auth token
    const requestInterceptor = axios.interceptors.request.use(
      (config) => {
        // Only add token if we have one and user is authenticated
        if (token && user) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );
    
    // Add response interceptor for auth errors
    const responseInterceptor = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        // Only log auth errors if we expect to be authenticated
        if (error.response?.status === 401 && user) {
          if (window.__EP_DEBUG_ENABLED__) {
            const bus = getDebugBus();
            bus.emit({
              type: 'auth.error',
              message: '401 Unauthorized - Token may be expired',
              url: error.config?.url
            });
          }
        }
        return Promise.reject(error);
      }
    );
    
    return () => {
      axios.interceptors.request.eject(requestInterceptor);
      axios.interceptors.response.eject(responseInterceptor);
    };
  }, [token, user]);
  
  // Check authentication on mount
  useEffect(() => {
    checkAuth();
  }, []);
  
  const checkAuth = async () => {
    try {
      const storedToken = localStorage.getItem('emailpilot-token');
      if (!storedToken) {
        setLoading(false);
        return;
      }
      
      setToken(storedToken);
      
      // Verify token is valid
      const response = await axios.get('/api/auth/me', {
        headers: { Authorization: `Bearer ${storedToken}` }
      });
      
      setUser(response.data);
    } catch (error) {
      // Token is invalid or expired
      localStorage.removeItem('emailpilot-token');
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };
  
  const signIn = async (email: string, password: string) => {
    try {
      const response = await axios.post('/api/auth/login', { email, password });
      const { access_token, user: userData } = response.data;
      
      // Store token
      localStorage.setItem('emailpilot-token', access_token);
      setToken(access_token);
      setUser(userData);
      
      return { success: true };
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail || 'Login failed';
      
      if (window.__EP_DEBUG_ENABLED__) {
        const bus = getDebugBus();
        bus.emit({
          type: 'auth.error',
          message: `Login failed: ${errorMessage}`,
          stack: error.stack
        });
      }
      
      return { success: false, error: errorMessage };
    }
  };
  
  const signOut = async () => {
    try {
      await axios.post('/api/auth/logout');
    } catch (error) {
      // Ignore logout errors
    } finally {
      localStorage.removeItem('emailpilot-token');
      setToken(null);
      setUser(null);
    }
  };
  
  const value: AuthContextType = {
    user,
    token,
    loading,
    signIn,
    signOut,
    isAuthenticated: !!user && !!token
  };
  
  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}