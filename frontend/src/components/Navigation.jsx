import React from 'react';
import { NavLink } from 'react-router-dom';
import { useSelector, useDispatch } from 'react-redux';
import { logout } from '../store/authSlice';

const Navigation = () => {
    const { token, user } = useSelector(state => state.auth);
    const dispatch = useDispatch();

    if (!token) return null;

    return (
        <nav className="glass-card" style={{ padding: '1rem', marginBottom: '2rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '2rem' }}>
                <NavLink to="/" style={({ isActive }) => ({ color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 })}>
                    Dashboard
                </NavLink>
                <NavLink to="/members" style={({ isActive }) => ({ color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 })}>
                    Members
                </NavLink>
                <NavLink to="/sessions" style={({ isActive }) => ({ color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 })}>
                    Sessions
                </NavLink>
                <NavLink to="/stats" style={({ isActive }) => ({ color: isActive ? 'var(--primary-color)' : 'var(--text-secondary)', textDecoration: 'none', fontWeight: 600 })}>
                    Insights
                </NavLink>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                    {user?.firstname} {user?.lastname}
                </span>
                <button
                    className="btn"
                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', background: 'var(--error-color)' }}
                    onClick={() => dispatch(logout())}
                >
                    Logout
                </button>
            </div>
        </nav>
    );
};

export default Navigation;
