import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

function ResetPassword() {
    const [step, setStep] = useState(1); // 1: Request, 2: Reset
    const [login, setLogin] = useState('');
    const [otp, setOtp] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const navigate = useNavigate();

    const handleRequest = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await axios.post('/auth/forgot-password', null, { params: { login } });
            setStep(2);
        } catch (err) {
            setError(err.response?.data?.detail || 'Request failed');
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        try {
            await axios.post('/auth/reset-password', { login, otp }, { params: { new_password: newPassword } });
            alert('Password reset successfully!');
            navigate('/login');
        } catch (err) {
            setError(err.response?.data?.detail || 'Reset failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{ maxWidth: '400px', margin: '100px auto', padding: '0 1rem' }}>
            <div className="glass-card">
                <h1 style={{ textAlign: 'center' }}>Reset Password</h1>
                {error && <p style={{ color: 'var(--error-color)', textAlign: 'center' }}>{error}</p>}

                {step === 1 ? (
                    <form onSubmit={handleRequest}>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', textAlign: 'center' }}>
                            Enter your email or phone number to receive a reset code.
                        </p>
                        <input
                            placeholder="Email or Phone"
                            value={login}
                            onChange={e => setLogin(e.target.value)}
                            required
                        />
                        <button className="btn" style={{ width: '100%' }} disabled={loading}>
                            {loading ? 'Sending Code...' : 'Send Reset Code'}
                        </button>
                    </form>
                ) : (
                    <form onSubmit={handleReset}>
                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', textAlign: 'center' }}>
                            Enter the code and your new password.
                        </p>
                        <input
                            placeholder="6-digit Code"
                            value={otp}
                            onChange={e => setOtp(e.target.value)}
                            required
                        />
                        <input
                            type="password"
                            placeholder="New Password"
                            value={newPassword}
                            onChange={e => setNewPassword(e.target.value)}
                            required
                        />
                        <button className="btn" style={{ width: '100%' }} disabled={loading}>
                            {loading ? 'Resetting...' : 'Reset Password'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
}

export default ResetPassword;
