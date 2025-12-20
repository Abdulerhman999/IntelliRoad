import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import AdminDashboard from './components/AdminDashboard';
import NewProject from './components/NewProject';
import ProjectDetailsWithTabs from './components/ProjectDetailsWithTabs';
import ManageMaterialPrices from './components/ManageMaterialPrices';
import CreateEmployee from './components/CreateEmployee';
import AddTrainingData from './components/AddTrainingData';
import ChangePassword from './components/ChangePassword';
import ModelTraining from './components/ModelTraining';
import './App.css';

function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (error) {
        console.error('Failed to parse saved user:', error);
        localStorage.removeItem('user');
      }
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    localStorage.setItem('user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    localStorage.removeItem('user');
  };

  return (
    <Router>
      <div className="App">
        {user && <Navbar user={user} onLogout={handleLogout} />}

        <Routes>
          {/* Public Routes */}
          <Route
            path="/login"
            element={!user ? <Login onLogin={handleLogin} /> : <Navigate to="/dashboard" />}
          />

          {/* Protected Routes - Dashboard */}
          <Route
            path="/dashboard"
            element={
              user ? (
                user.role === 'admin' ? <AdminDashboard user={user} /> : <Dashboard user={user} />
              ) : <Navigate to="/login" />
            }
          />

          {/* Project Routes */}
          <Route
            path="/new-project"
            element={user ? <NewProject user={user} /> : <Navigate to="/login" />}
          />

          <Route
            path="/project/:projectId/details"
            element={user ? <ProjectDetailsWithTabs user={user} /> : <Navigate to="/login" />}
          />
          {/* Change Password Routes */}
          <Route
            path="/change-password"
            element={user ? <ChangePassword user={user} /> : <Navigate to="/login" />}
          />
          <Route
            path="/change-password"
            element={user ? <ChangePassword user={user} /> : <Navigate to="/login" />}
          />
          {/* Admin Routes */}
          <Route
            path="/admin/manage-prices"
            element={
              user && user.role === 'admin' ?
                <ManageMaterialPrices user={user} /> :
                <Navigate to="/dashboard" />
            }
          />

          <Route
            path="/admin/create-user"
            element={
              user && user.role === 'admin' ?
                <CreateEmployee user={user} /> :
                <Navigate to="/dashboard" />
            }
          />

          <Route
            path="/admin/add-training-data"
            element={
              user && user.role === 'admin' ?
                <AddTrainingData user={user} /> :
                <Navigate to="/dashboard" />
            }
          />
          <Route
            path="/admin/model-training"
            element={
              user && user.role === 'admin' ?
                <ModelTraining user={user} /> :
                <Navigate to="/dashboard" />
            }
          />

          {/* Default Route */}
          <Route
            path="/"
            element={<Navigate to={user ? "/dashboard" : "/login"} />}
          />

          {/* 404 Route */}
          <Route
            path="*"
            element={<Navigate to={user ? "/dashboard" : "/login"} />}
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;