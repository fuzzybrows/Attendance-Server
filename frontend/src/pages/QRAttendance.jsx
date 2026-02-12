import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import axios from 'axios';

function QRAttendance() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { token: authToken, user } = useSelector(state => state.auth);

    const sessionId = searchParams.get('session_id');
    const qrToken = searchParams.get('token');

    const [status, setStatus] = useState('processing'); // processing, success, error, login_required
    const [message, setMessage] = useState('');
    const [memberName, setMemberName] = useState('');

    useEffect(() => {
        if (!sessionId || !qrToken) {
            setStatus('error');
            setMessage('Invalid QR code link.');
            return;
        }

        if (!authToken) {
            setStatus('login_required');
            setMessage('Please log in first, then scan the QR code again.');
            return;
        }

        // Mark attendance
        const markAttendance = async () => {
            try {
                const response = await axios.post(
                    `/attendance/qr/mark?session_id=${sessionId}&qr_token=${qrToken}`,
                    {},
                    { headers: { Authorization: `Bearer ${authToken}` } }
                );
                setStatus('success');
                setMessage(response.data.message);
                setMemberName(response.data.member_name);
            } catch (err) {
                setStatus('error');
                if (err.response?.status === 409) {
                    setMessage('Your attendance has already been recorded for this session.');
                } else if (err.response?.status === 401) {
                    setMessage(err.response.data.detail || 'QR code has expired. Please scan again.');
                } else {
                    setMessage(err.response?.data?.detail || 'Something went wrong. Please try again.');
                }
            }
        };

        markAttendance();
    }, [sessionId, qrToken, authToken]);

    return (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
            <div className="glass-card" style={{ maxWidth: '480px', width: '100%', textAlign: 'center', padding: '2.5rem' }}>
                {status === 'processing' && (
                    <>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⏳</div>
                        <h2>Marking Attendance...</h2>
                        <p style={{ color: 'var(--text-secondary)' }}>Please wait while we record your attendance.</p>
                    </>
                )}

                {status === 'success' && (
                    <>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✅</div>
                        <h2 style={{ color: '#4ade80' }}>Attendance Marked!</h2>
                        <p style={{ fontSize: '1.1rem', marginTop: '0.5rem' }}>{message}</p>
                        <Link to="/" className="btn" style={{ display: 'inline-block', marginTop: '1.5rem' }}>
                            Go to Dashboard
                        </Link>
                    </>
                )}

                {status === 'error' && (
                    <>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>❌</div>
                        <h2 style={{ color: '#ff6b6b' }}>Error</h2>
                        <p style={{ marginTop: '0.5rem' }}>{message}</p>
                        <Link to="/" className="btn" style={{ display: 'inline-block', marginTop: '1.5rem' }}>
                            Go to Dashboard
                        </Link>
                    </>
                )}

                {status === 'login_required' && (
                    <>
                        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🔒</div>
                        <h2>Login Required</h2>
                        <p style={{ marginTop: '0.5rem' }}>{message}</p>
                        <Link
                            to={`/login?redirect=${encodeURIComponent(window.location.pathname + window.location.search)}`}
                            className="btn"
                            style={{ display: 'inline-block', marginTop: '1.5rem' }}
                        >
                            Log In
                        </Link>
                    </>
                )}
            </div>
        </div>
    );
}

export default QRAttendance;
