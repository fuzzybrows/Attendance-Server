import React from 'react';
import { NavLink } from 'react-router-dom';

const Navigation = () => {
    return (
        <nav className="glass-card" style={{ padding: '1rem', marginBottom: '2rem', display: 'flex', gap: '2rem' }}>
            <NavLink
                to="/"
                style={({ isActive }) => ({
                    color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)',
                    textDecoration: 'none',
                    fontWeight: 600
                })}
            >
                Dashboard
            </NavLink>
            <NavLink
                to="/stats"
                style={({ isActive }) => ({
                    color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)',
                    textDecoration: 'none',
                    fontWeight: 600
                })}
            >
                Insights & Statistics
            </NavLink>
        </nav>
    );
};

export default Navigation;
