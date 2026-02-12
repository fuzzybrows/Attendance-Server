import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import Statistics from './pages/Statistics';
import Login from './pages/Login';
import VerifyOTP from './pages/VerifyOTP';
import ResetPassword from './pages/ResetPassword';
import MembersManagement from './pages/MembersManagement';
import Sessions from './pages/Sessions';
import QRAttendance from './pages/QRAttendance';

const ProtectedRoute = ({ children }) => {
  const { token } = useSelector(state => state.auth);
  if (!token) return <Navigate to="/login" />;
  return children;
};

function App() {
  return (
    <Router>
      <div className="container">
        <Navigation />
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/verify" element={<VerifyOTP />} />
          <Route path="/forgot-password" element={<ResetPassword />} />
          <Route path="/qr-attendance" element={<QRAttendance />} />

          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/members" element={<ProtectedRoute><MembersManagement /></ProtectedRoute>} />
          <Route path="/sessions" element={<ProtectedRoute><Sessions /></ProtectedRoute>} />
          <Route path="/stats" element={<ProtectedRoute><Statistics /></ProtectedRoute>} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;

