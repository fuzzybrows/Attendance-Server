import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import Dashboard from './pages/Dashboard';
import Statistics from './pages/Statistics';

function App() {
  return (
    <Router>
      <div className="container">
        <Navigation />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/stats" element={<Statistics />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
