import React from "react";
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
// import { useAuth } from '@clerk/clerk-react';  // DISABLED FOR LOCAL DEV
import Login from "./components/Login.jsx";
import Dashboard from "./components/Dashboard.jsx";

function App() {
    // BYPASSED: Authentication disabled for local development
    // const { isSignedIn, isLoaded } = useAuth();
    const isSignedIn = true;  // Always authenticated in local dev
    const isLoaded = true;

    if (!isLoaded) {
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
                        isSignedIn ? <Dashboard /> : <Navigate to="/login" />
                    }
                />
                <Route
                    path="*"
                    element={<Navigate to={isSignedIn ? "/dashboard" : "/login"} />}
                />
            </Routes>
        </HashRouter>
    );
}

export default App;