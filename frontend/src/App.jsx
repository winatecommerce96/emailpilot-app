import React, { useState, useEffect } from "react";
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from "./components/Login.jsx";
import Dashboard from "./components/Dashboard.jsx";

function App() {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const verifySession = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setIsAuthenticated(false);
                setIsLoading(false);
                return;
            }

            try {
                const response = await fetch('/api/auth/google/me', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
                if (response.ok) {
                    setIsAuthenticated(true);
                } else {
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('session_id');
                    setIsAuthenticated(false);
                }
            } catch (error) {
                console.error("Session verification failed:", error);
                setIsAuthenticated(false);
            } finally {
                setIsLoading(false);
            }
        };

        verifySession();
    }, []);

    if (isLoading) {
        return (
            <div className="card">
                <h1>Loading...</h1>
            </div>
        );
    }

    return (
        <HashRouter>
            <Routes>
                <Route path="/login" element={<Login />} />
                <Route
                    path="/dashboard/*"
                    element={
                        isAuthenticated ? <Dashboard /> : <Navigate to="/login" />
                    }
                />
                <Route 
                    path="*" 
                    element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} />} 
                />
            </Routes>
        </HashRouter>
    );
}

export default App;