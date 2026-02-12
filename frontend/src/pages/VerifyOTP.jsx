import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { verifyOTP } from '../store/authSlice';

function VerifyOTP() {
    const [otp, setOtp] = useState('');
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { token, needsVerification, loading, error } = useSelector(state => state.auth);

    useEffect(() => {
        if (token) navigate('/');
        if (!needsVerification) navigate('/login');
    }, [token, needsVerification, navigate]);

    const handleVerify = (e) => {
        e.preventDefault();
        dispatch(verifyOTP({ login: needsVerification.login, otp }));
    };

    return (
        <div style={{ maxWidth: '400px', margin: '100px auto', padding: '0 1rem' }}>
            <div className="glass-card" style={{ textAlign: 'center' }}>
                <h1>Verify {needsVerification?.method}</h1>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                    An OTP has been sent to your {needsVerification?.method}. Please enter it below.
                </p>
                {error && <p style={{ color: 'var(--error-color)' }}>{error}</p>}
                <form onSubmit={handleVerify}>
                    <input
                        placeholder="6-digit OTP"
                        value={otp}
                        onChange={e => setOtp(e.target.value)}
                        maxLength={6}
                        style={{ textAlign: 'center', fontSize: '1.5rem', letterSpacing: '0.5rem' }}
                        required
                    />
                    <button className="btn" style={{ width: '100%', marginTop: '1rem' }} disabled={loading}>
                        {loading ? 'Verifying...' : 'Verify & Continue'}
                    </button>
                </form>
            </div>
        </div>
    );
}

export default VerifyOTP;
