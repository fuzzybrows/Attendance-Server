import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate, Link } from 'react-router-dom';
import { login, clearError } from '../store/authSlice';

function Login() {
    const [credentials, setCredentials] = useState({ login: '', password: '' });
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { token, loading, error, needsVerification } = useSelector(state => state.auth);

    useEffect(() => {
        if (token) navigate('/');
        if (needsVerification) navigate('/verify');
    }, [token, needsVerification, navigate]);

    const handleSubmit = (e) => {
        e.preventDefault();
        dispatch(login({ login: credentials.login.trim(), password: credentials.password.trim() }));
    };

    return (
        <div style={{ maxWidth: '400px', margin: '100px auto', padding: '0 1rem' }}>
            <div className="glass-card">
                <h1 style={{ textAlign: 'center' }}>Login</h1>
                {error && <p style={{ color: 'var(--error-color)', textAlign: 'center' }}>{error}</p>}
                <form onSubmit={handleSubmit}>
                    <input
                        placeholder="Email or Phone Number"
                        value={credentials.login}
                        onChange={e => setCredentials({ ...credentials, login: e.target.value })}
                        required
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={credentials.password}
                        onChange={e => setCredentials({ ...credentials, password: e.target.value })}
                        required
                    />
                    <button className="btn" style={{ width: '100%' }} disabled={loading}>
                        {loading ? 'Logging in...' : 'Login'}
                    </button>
                </form>
                <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem' }}>
                    <Link to="/forgot-password" style={{ color: 'var(--text-secondary)' }}>Forgot password?</Link>
                </div>
            </div>
        </div>
    );
}

export default Login;
