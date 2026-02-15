import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { fetchMembers, addMember } from '../store/membersSlice';
import { fetchSessions, addSession, setCurrentSession, deleteSession, bulkDeleteSessions } from '../store/sessionsSlice';
import { fetchAttendance, submitAttendance, deleteAttendance, bulkDeleteAttendance } from '../store/attendanceSlice';
import Modal from '../components/Modal';
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import axios from 'axios';
import { QRCodeSVG } from 'qrcode.react';
import { Html5Qrcode } from 'html5-qrcode';

function Dashboard() {
    const dispatch = useDispatch();
    const { items: members } = useSelector(state => state.members);
    const { items: sessions, currentSession } = useSelector(state => state.sessions);
    const { items: attendance } = useSelector(state => state.attendance);
    const { user } = useSelector(state => state.auth);

    const isAdmin = user?.permissions?.includes('admin');

    const [isMemberModalOpen, setMemberModalOpen] = useState(false);
    const [isSessionModalOpen, setSessionModalOpen] = useState(false);

    const [newMember, setNewMember] = useState({ first_name: '', last_name: '', email: '', nfc_id: '' });
    const [newSession, setNewSession] = useState({ title: '', type: 'rehearsal', start_time: new Date() });

    // Delete confirmation state
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deletePassword, setDeletePassword] = useState('');
    const [deleteError, setDeleteError] = useState('');
    const [deleteLoading, setDeleteLoading] = useState(false);

    // Multi-select state
    const [selectedSessions, setSelectedSessions] = useState(new Set());
    const [selectedAttendance, setSelectedAttendance] = useState(new Set());

    // QR Scanner state (members)
    const [scannerActive, setScannerActive] = useState(false);
    const [scannerStatus, setScannerStatus] = useState(''); // '', 'starting', 'scanning', 'success', 'error'
    const [scannerMessage, setScannerMessage] = useState('');
    const scannerRef = useRef(null);
    const navigate = useNavigate();

    // Start scanner AFTER the div is rendered in the DOM
    useEffect(() => {
        if (!scannerActive) return;

        const timeoutId = setTimeout(async () => {
            const el = document.getElementById('qr-scanner-region');
            if (!el) {
                setScannerStatus('error');
                setScannerMessage('Scanner container not found. Please try again.');
                return;
            }

            // Camera API requires HTTPS on mobile (localhost is exempt)
            const isSecure = window.location.protocol === 'https:' ||
                window.location.hostname === 'localhost' ||
                window.location.hostname === '127.0.0.1';
            if (!isSecure) {
                setScannerStatus('error');
                setScannerMessage(
                    'Camera requires a secure (HTTPS) connection on mobile devices. ' +
                    'Please use your phone\'s camera app to scan the QR code directly instead.'
                );
                return;
            }

            try {
                const html5QrCode = new Html5Qrcode('qr-scanner-region');
                scannerRef.current = html5QrCode;

                const scanConfig = { fps: 10, qrbox: { width: 250, height: 250 } };
                const onSuccess = (decodedText) => {
                    setScannerStatus('success');
                    setScannerMessage('QR code scanned! Marking attendance...');
                    html5QrCode.stop().catch(() => { });
                    scannerRef.current = null;
                    try {
                        const url = new URL(decodedText);
                        if (url.pathname === '/qr-attendance') {
                            navigate(url.pathname + url.search);
                        } else {
                            window.location.href = decodedText;
                        }
                    } catch {
                        window.location.href = decodedText;
                    }
                };
                const onIgnore = () => { };

                // Try rear camera, then front camera, then any available camera
                let started = false;
                try {
                    await html5QrCode.start({ facingMode: 'environment' }, scanConfig, onSuccess, onIgnore);
                    started = true;
                } catch { /* try next */ }

                if (!started) {
                    try {
                        await html5QrCode.start({ facingMode: 'user' }, scanConfig, onSuccess, onIgnore);
                        started = true;
                    } catch { /* try next */ }
                }

                if (!started) {
                    const devices = await Html5Qrcode.getCameras();
                    if (devices && devices.length > 0) {
                        await html5QrCode.start(devices[0].id, scanConfig, onSuccess, onIgnore);
                        started = true;
                    }
                }

                if (!started) {
                    throw new Error('No cameras found');
                }

                setScannerStatus('scanning');
                setScannerMessage('Point your camera at the QR code');
            } catch (err) {
                setScannerStatus('error');
                const errStr = (err?.message || err?.toString?.() || '');
                if (errStr.includes('NotAllowed') || errStr.includes('Permission')) {
                    setScannerMessage('Camera permission denied. Please allow camera access in your browser settings and try again.');
                } else if (errStr.includes('NotFound') || errStr.includes('No cameras')) {
                    setScannerMessage('No camera found. Use your phone\'s camera app to scan the QR code instead.');
                } else if (errStr.includes('NotReadable') || errStr.includes('in use')) {
                    setScannerMessage('Camera is in use by another app. Close other apps and try again.');
                } else {
                    setScannerMessage('Could not access camera. Try using your phone\'s camera app to scan the QR code directly.');
                }
            }
        }, 150);

        return () => {
            clearTimeout(timeoutId);
            if (scannerRef.current) {
                scannerRef.current.stop().catch(() => { });
                scannerRef.current = null;
            }
        };
    }, [scannerActive, navigate]);

    // QR code state
    const [qrUrl, setQrUrl] = useState('');
    const [qrCountdown, setQrCountdown] = useState(0);
    const [qrActive, setQrActive] = useState(false);
    const qrIntervalRef = useRef(null);
    const countdownRef = useRef(null);

    const QR_REFRESH_SECONDS = 25;

    const fetchQrToken = useCallback(async (sessionId) => {
        try {
            const res = await axios.get(`/attendance/qr/token/${sessionId}`);
            const token = res.data.token;
            const baseUrl = window.location.origin;
            setQrUrl(`${baseUrl}/qr-attendance?session_id=${sessionId}&token=${token}`);
            setQrCountdown(QR_REFRESH_SECONDS);
        } catch (e) {
            console.error('Failed to fetch QR token', e);
        }
    }, []);

    // QR auto-refresh
    useEffect(() => {
        if (qrActive && currentSession && isAdmin) {
            fetchQrToken(currentSession.id);
            qrIntervalRef.current = setInterval(() => {
                fetchQrToken(currentSession.id);
            }, QR_REFRESH_SECONDS * 1000);

            countdownRef.current = setInterval(() => {
                setQrCountdown(prev => (prev > 0 ? prev - 1 : QR_REFRESH_SECONDS));
            }, 1000);

            return () => {
                clearInterval(qrIntervalRef.current);
                clearInterval(countdownRef.current);
            };
        } else {
            setQrUrl('');
            return () => {
                clearInterval(qrIntervalRef.current);
                clearInterval(countdownRef.current);
            };
        }
    }, [qrActive, currentSession, isAdmin, fetchQrToken]);

    useEffect(() => {
        dispatch(fetchMembers());
        dispatch(fetchSessions());
    }, [dispatch]);

    useEffect(() => {
        if (currentSession) {
            dispatch(fetchAttendance(currentSession.id));
        }
    }, [currentSession, dispatch]);

    const handleAddMember = () => {
        dispatch(addMember({
            ...newMember,
            first_name: newMember.first_name.trim(),
            last_name: newMember.last_name.trim(),
            email: newMember.email.trim(),
            nfc_id: newMember.nfc_id.trim()
        }));
        setMemberModalOpen(false);
        setNewMember({ first_name: '', last_name: '', email: '', nfc_id: '' });
    };

    const handleAddSession = () => {
        if (!newSession.start_time) {
            alert("Please specify a start time.");
            return;
        }
        // Convert Date object to ISO string for the backend
        const sessionData = {
            ...newSession,
            title: newSession.title.trim(),
            start_time: newSession.start_time.toISOString()
        };
        dispatch(addSession(sessionData));
        setSessionModalOpen(false);
        setNewSession({ title: '', type: 'rehearsal', start_time: new Date() });
    };

    const handleMarkAttendance = async (memberId) => {
        if (!currentSession) return;

        let location = { lat: null, lng: null };
        try {
            const pos = await new Promise((resolve, reject) => {
                navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
            });
            location.lat = pos.coords.latitude;
            location.lng = pos.coords.longitude;
        } catch (e) {
            console.warn("GPS failed", e);
        }

        dispatch(submitAttendance({
            member_id: memberId,
            session_id: currentSession.id,
            latitude: location.lat,
            longitude: location.lng,
            submission_type: 'manual',
            marked_by_id: user?.id || null
        }));
    };

    const requestDelete = (type, id, label) => {
        setDeleteTarget({ type, id, label });
        setDeletePassword('');
        setDeleteError('');
    };

    const requestBulkDelete = (type) => {
        const ids = type === 'session' ? [...selectedSessions] : [...selectedAttendance];
        if (ids.length === 0) return;
        setDeleteTarget({ type: `bulk-${type}`, ids, label: `${ids.length} ${type === 'session' ? 'session' : 'attendance record'}${ids.length > 1 ? 's' : ''}` });
        setDeletePassword('');
        setDeleteError('');
    };

    const handleConfirmDelete = async () => {
        if (!deletePassword) {
            setDeleteError('Password is required');
            return;
        }
        setDeleteLoading(true);
        setDeleteError('');

        try {
            // Verify password first by attempting login
            const loginId = user?.email || '';
            await axios.post('/auth/login', { login: loginId, password: deletePassword });

            // Password verified — proceed with delete
            if (deleteTarget.type === 'session') {
                await dispatch(deleteSession(deleteTarget.id)).unwrap();
            } else if (deleteTarget.type === 'attendance') {
                await dispatch(deleteAttendance(deleteTarget.id)).unwrap();
            } else if (deleteTarget.type === 'bulk-session') {
                await dispatch(bulkDeleteSessions(deleteTarget.ids)).unwrap();
                setSelectedSessions(new Set());
            } else if (deleteTarget.type === 'bulk-attendance') {
                await dispatch(bulkDeleteAttendance(deleteTarget.ids)).unwrap();
                setSelectedAttendance(new Set());
            }
            setDeleteTarget(null);
            setDeletePassword('');
        } catch (err) {
            if (err.response?.status === 401) {
                setDeleteError('Invalid password');
            } else if (err.message) {
                setDeleteError(err.message);
            } else {
                setDeleteError('Invalid password');
            }
        } finally {
            setDeleteLoading(false);
        }
    };

    return (
        <>
            <div className="grid">
                <div className="glass-card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h2>Active Sessions</h2>
                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                            {isAdmin && selectedSessions.size > 0 && (
                                <button
                                    className="btn"
                                    style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                                    onClick={() => requestBulkDelete('session')}
                                >
                                    🗑️ Delete {selectedSessions.size} selected
                                </button>
                            )}
                            {isAdmin && (
                                <button className="btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }} onClick={() => navigate('/sessions')}>
                                    View All Sessions →
                                </button>
                            )}
                        </div>
                    </div>
                    {(() => {
                        const activeSessions = sessions.filter(s => s.status === 'active' || !s.status);
                        if (activeSessions.length === 0) {
                            return <p style={{ color: 'var(--text-secondary)' }}>No active sessions.</p>;
                        }
                        return (
                            <>
                                {isAdmin && activeSessions.length > 0 && (
                                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem', cursor: 'pointer', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                                        <input
                                            type="checkbox"
                                            checked={activeSessions.length > 0 && selectedSessions.size === activeSessions.length}
                                            onChange={(e) => {
                                                if (e.target.checked) {
                                                    setSelectedSessions(new Set(activeSessions.map(s => s.id)));
                                                } else {
                                                    setSelectedSessions(new Set());
                                                }
                                            }}
                                            style={{ accentColor: '#818cf8' }}
                                        />
                                        Select All
                                    </label>
                                )}
                                <div id="sessions-list" style={{ maxHeight: '140px', overflowY: 'auto', position: 'relative' }}>
                                    {activeSessions.map(s => (
                                        <div key={s.id} className="glass-card" style={{ padding: '1rem', marginBottom: '0.5rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center', border: selectedSessions.has(s.id) ? '1px solid rgba(129, 140, 248, 0.4)' : undefined }} onClick={() => dispatch(setCurrentSession(s))}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                {isAdmin && (
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedSessions.has(s.id)}
                                                        onChange={(e) => {
                                                            e.stopPropagation();
                                                            const next = new Set(selectedSessions);
                                                            if (e.target.checked) next.add(s.id);
                                                            else next.delete(s.id);
                                                            setSelectedSessions(next);
                                                        }}
                                                        onClick={(e) => e.stopPropagation()}
                                                        style={{ accentColor: '#818cf8' }}
                                                    />
                                                )}
                                                <div>
                                                    <strong>{s.title}</strong><br />
                                                    <small>{new Date(s.start_time).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}</small>
                                                </div>
                                            </div>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <span className={`status-badge ${s.type === 'rehearsal' ? 'status-nfc' : 'status-manual'}`}>{s.type}</span>
                                                {isAdmin && (
                                                    <button
                                                        className="btn"
                                                        style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
                                                        onClick={(e) => { e.stopPropagation(); requestDelete('session', s.id, s.title); }}
                                                    >
                                                        🗑️ Delete
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                {activeSessions.length > 1 && (
                                    <p style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.25rem', animation: 'pulse 2s ease-in-out infinite' }}>
                                        ↕ Scroll to see more active sessions
                                    </p>
                                )}
                            </>
                        );
                    })()}
                    {isAdmin && (
                        <button className="btn" style={{ marginTop: '0.75rem' }} onClick={() => setSessionModalOpen(true)}>+ New Session</button>
                    )}
                </div>
            </div>

            <div className="glass-card">
                <h2>{currentSession ? `Attendance: ${currentSession.title}` : 'Attendance Records'}</h2>
                {!currentSession ? (
                    <p>Select a session to view attendance.</p>
                ) : (
                    <div>
                        {/* QR Code Section */}
                        {isAdmin && (
                            <div style={{
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                padding: '1.5rem',
                                marginBottom: '1.5rem',
                                borderRadius: '12px',
                                background: qrActive ? 'rgba(74, 222, 128, 0.08)' : 'rgba(255,255,255,0.03)',
                                border: qrActive ? '1px solid rgba(74, 222, 128, 0.2)' : '1px solid rgba(255,255,255,0.1)',
                                transition: 'all 0.3s ease'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', width: '100%', justifyContent: 'space-between', marginBottom: qrActive ? '1rem' : 0 }}>
                                    <div>
                                        <h3 style={{ margin: 0 }}>📱 QR Attendance</h3>
                                        <small style={{ color: 'var(--text-secondary)' }}>
                                            {qrActive ? 'Members can scan this code to mark attendance' : 'Enable to show QR code for members'}
                                        </small>
                                    </div>
                                    <button
                                        className="btn"
                                        style={{
                                            background: qrActive ? 'rgba(255,50,50,0.2)' : 'rgba(74,222,128,0.2)',
                                            border: qrActive ? '1px solid rgba(255,50,50,0.4)' : '1px solid rgba(74,222,128,0.4)',
                                            color: qrActive ? '#ff6b6b' : '#4ade80',
                                            padding: '0.4rem 1rem',
                                            fontSize: '0.85rem'
                                        }}
                                        onClick={() => setQrActive(!qrActive)}
                                    >
                                        {qrActive ? '⏹ Stop' : '▶ Start'}
                                    </button>
                                </div>

                                {qrActive && qrUrl && (
                                    <>
                                        <div style={{
                                            background: '#ffffff',
                                            padding: '16px',
                                            borderRadius: '12px',
                                            display: 'inline-block',
                                            boxShadow: '0 4px 24px rgba(0,0,0,0.3)'
                                        }}>
                                            <QRCodeSVG
                                                value={qrUrl}
                                                size={220}
                                                level="M"
                                                includeMargin={false}
                                            />
                                        </div>
                                        <div style={{ marginTop: '0.75rem', textAlign: 'center' }}>
                                            <div style={{
                                                display: 'inline-flex',
                                                alignItems: 'center',
                                                gap: '0.5rem',
                                                padding: '0.3rem 0.8rem',
                                                borderRadius: '20px',
                                                background: 'rgba(255,255,255,0.05)',
                                                fontSize: '0.85rem'
                                            }}>
                                                🔄 Refreshes in <strong style={{ color: qrCountdown <= 5 ? '#ff6b6b' : '#4ade80' }}>{qrCountdown}s</strong>
                                            </div>
                                        </div>
                                    </>
                                )}
                            </div>
                        )}

                        {!isAdmin && (
                            <div style={{
                                textAlign: 'center',
                                padding: '1.5rem',
                                marginBottom: '1.5rem',
                                borderRadius: '12px',
                                background: scannerActive ? 'rgba(99, 102, 241, 0.12)' : 'rgba(99, 102, 241, 0.08)',
                                border: '1px solid rgba(99, 102, 241, 0.2)',
                                transition: 'all 0.3s ease'
                            }}>
                                {!scannerActive ? (
                                    <>
                                        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📷</div>
                                        <p style={{ margin: '0 0 1rem 0' }}>Scan the QR code displayed by your admin to mark your attendance.</p>
                                        <button
                                            className="btn"
                                            style={{
                                                background: 'rgba(99, 102, 241, 0.2)',
                                                border: '1px solid rgba(99, 102, 241, 0.4)',
                                                color: '#818cf8',
                                                padding: '0.6rem 1.5rem',
                                                fontSize: '0.95rem',
                                                cursor: 'pointer'
                                            }}
                                            onClick={() => {
                                                setScannerActive(true);
                                                setScannerStatus('starting');
                                                setScannerMessage('Requesting camera access...');
                                            }}
                                        >
                                            📱 Open Scanner
                                        </button>
                                    </>
                                ) : (
                                    <>
                                        <div
                                            id="qr-scanner-region"
                                            style={{
                                                width: '100%',
                                                maxWidth: '400px',
                                                margin: '0 auto',
                                                borderRadius: '12px',
                                                overflow: 'hidden',
                                                minHeight: scannerStatus === 'scanning' ? '300px' : '50px'
                                            }}
                                        />
                                        <p style={{
                                            marginTop: '0.75rem',
                                            marginBottom: '0.5rem',
                                            color: scannerStatus === 'success' ? '#4ade80'
                                                : scannerStatus === 'error' ? '#ff6b6b'
                                                    : 'var(--text-secondary)',
                                            fontSize: '0.9rem'
                                        }}>
                                            {scannerStatus === 'starting' && '⏳ '}
                                            {scannerStatus === 'scanning' && '🔍 '}
                                            {scannerStatus === 'success' && '✅ '}
                                            {scannerStatus === 'error' && '❌ '}
                                            {scannerMessage}
                                        </p>
                                        {scannerStatus !== 'success' && (
                                            <button
                                                className="btn"
                                                style={{
                                                    background: 'rgba(255,50,50,0.2)',
                                                    border: '1px solid rgba(255,50,50,0.4)',
                                                    color: '#ff6b6b',
                                                    padding: '0.4rem 1rem',
                                                    fontSize: '0.85rem'
                                                }}
                                                onClick={() => {
                                                    if (scannerRef.current) {
                                                        scannerRef.current.stop().catch(() => { });
                                                        scannerRef.current = null;
                                                    }
                                                    setScannerActive(false);
                                                    setScannerStatus('');
                                                    setScannerMessage('');
                                                }}
                                            >
                                                Close Scanner
                                            </button>
                                        )}
                                    </>
                                )}
                            </div>
                        )}
                        <table>
                            <thead>
                                <tr>
                                    {isAdmin && (
                                        <th style={{ width: '30px' }}>
                                            <input
                                                type="checkbox"
                                                checked={Array.isArray(attendance) && attendance.length > 0 && selectedAttendance.size === attendance.length}
                                                onChange={(e) => {
                                                    if (e.target.checked && Array.isArray(attendance)) {
                                                        setSelectedAttendance(new Set(attendance.map(a => a.id)));
                                                    } else {
                                                        setSelectedAttendance(new Set());
                                                    }
                                                }}
                                                style={{ accentColor: '#818cf8' }}
                                            />
                                        </th>
                                    )}
                                    <th>Member</th>
                                    <th>Time</th>
                                    <th>Type</th>
                                    <th>Marked By</th>
                                    <th>Location</th>
                                    {isAdmin && <th>Action</th>}
                                </tr>
                            </thead>
                            <tbody>
                                {Array.isArray(attendance) ? attendance.map(a => {
                                    const member = members.find(m => m.id === a.member_id);
                                    const markedBy = members.find(m => m.id === a.marked_by_id);
                                    const memberName = member ? `${member.first_name} ${member.last_name}` : 'Unknown';
                                    return (
                                        <tr key={a.id} style={{ background: selectedAttendance.has(a.id) ? 'rgba(129, 140, 248, 0.08)' : undefined }}>
                                            {isAdmin && (
                                                <td>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedAttendance.has(a.id)}
                                                        onChange={(e) => {
                                                            const next = new Set(selectedAttendance);
                                                            if (e.target.checked) next.add(a.id);
                                                            else next.delete(a.id);
                                                            setSelectedAttendance(next);
                                                        }}
                                                        style={{ accentColor: '#818cf8' }}
                                                    />
                                                </td>
                                            )}
                                            <td>{memberName}</td>
                                            <td>{new Date(a.timestamp).toLocaleTimeString()}</td>
                                            <td><span className={`status-badge status-${a.submission_type}`}>{a.submission_type}</span></td>
                                            <td>{markedBy ? `${markedBy.first_name} ${markedBy.last_name}` : 'Self'}</td>
                                            <td>{a.latitude ? `${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}` : 'N/A'}</td>
                                            {isAdmin && (
                                                <td>
                                                    <button
                                                        className="btn"
                                                        style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.2rem 0.5rem', fontSize: '0.75rem' }}
                                                        onClick={() => requestDelete('attendance', a.id, memberName)}
                                                    >
                                                        🗑️ Remove
                                                    </button>
                                                </td>
                                            )}
                                        </tr>
                                    );
                                }) : (
                                    <tr><td colSpan="7">Error: Attendance data is not a list. Type: {typeof attendance}</td></tr>
                                )}
                            </tbody>
                        </table>
                        {isAdmin && selectedAttendance.size > 0 && (
                            <div style={{ marginTop: '0.75rem', textAlign: 'right' }}>
                                <button
                                    className="btn"
                                    style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                                    onClick={() => requestBulkDelete('attendance')}
                                >
                                    🗑️ Delete {selectedAttendance.size} selected record{selectedAttendance.size > 1 ? 's' : ''}
                                </button>
                            </div>
                        )}
                        <div style={{ marginTop: '2rem' }}>
                            <h3>Mark Manual Attendance</h3>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {members.filter(m => !attendance.some(a => a.member_id === m.id)).map(m => (
                                    <button key={m.id} className="btn" style={{ background: 'rgba(255,255,255,0.1)' }} onClick={() => handleMarkAttendance(m.id)}>
                                        {m.first_name} {m.last_name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Modal title="Add New Member" isOpen={isMemberModalOpen} onClose={() => setMemberModalOpen(false)} onSubmit={handleAddMember}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <input placeholder="First Name" value={newMember.first_name} onChange={e => setNewMember({ ...newMember, first_name: e.target.value })} />
                    <input placeholder="Last Name" value={newMember.last_name} onChange={e => setNewMember({ ...newMember, last_name: e.target.value })} />
                </div>
                <input placeholder="Email Address" value={newMember.email} onChange={e => setNewMember({ ...newMember, email: e.target.value })} />
                <input placeholder="NFC ID (Optional)" value={newMember.nfc_id} onChange={e => setNewMember({ ...newMember, nfc_id: e.target.value })} />
            </Modal>

            <Modal title="New Session" isOpen={isSessionModalOpen} onClose={() => setSessionModalOpen(false)} onSubmit={handleAddSession}>
                <input placeholder="Session Title" value={newSession.title} onChange={e => setNewSession({ ...newSession, title: e.target.value })} />
                <label style={{ display: 'block', margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Scheduled Start Time</label>
                <DatePicker
                    selected={newSession.start_time}
                    onChange={(date) => setNewSession({ ...newSession, start_time: date })}
                    showTimeSelect
                    dateFormat="Pp"
                    className="date-picker-input"
                    wrapperClassName="date-picker-wrapper"
                />
                <label style={{ display: 'block', margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Session Type</label>
                <select value={newSession.type} onChange={e => setNewSession({ ...newSession, type: e.target.value })}>
                    <option value="rehearsal">Rehearsal</option>
                    <option value="program">Program</option>
                </select>
            </Modal>

            {/* Password Confirmation Modal for Delete */}
            {deleteTarget && (
                <div className="modal-overlay">
                    <div className="glass-card" style={{ maxWidth: '420px', width: '100%', margin: 0 }}>
                        <h2 style={{ color: '#ff6b6b' }}>⚠️ Confirm Delete</h2>
                        <p style={{ marginBottom: '0.5rem' }}>
                            You are about to delete {deleteTarget.type === 'session' ? 'session' : 'attendance for'}:{' '}
                            <strong>{deleteTarget.label}</strong>
                        </p>
                        {deleteTarget.type === 'session' && (
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                                This will also delete all attendance records for this session.
                            </p>
                        )}
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                            Enter your password to confirm:
                        </label>
                        <input
                            type="password"
                            placeholder="Password"
                            value={deletePassword}
                            onChange={e => { setDeletePassword(e.target.value); setDeleteError(''); }}
                            onKeyDown={e => e.key === 'Enter' && handleConfirmDelete()}
                            autoFocus
                        />
                        {deleteError && (
                            <p style={{ color: '#ff6b6b', fontSize: '0.85rem', marginTop: '0.5rem' }}>{deleteError}</p>
                        )}
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                            <button
                                className="btn"
                                style={{ background: 'transparent', border: '1px solid var(--text-secondary)' }}
                                onClick={() => setDeleteTarget(null)}
                                disabled={deleteLoading}
                            >
                                Cancel
                            </button>
                            <button
                                className="btn"
                                style={{ background: 'rgba(255,50,50,0.3)', border: '1px solid rgba(255,50,50,0.6)', color: '#ff6b6b' }}
                                onClick={handleConfirmDelete}
                                disabled={deleteLoading || !deletePassword}
                            >
                                {deleteLoading ? 'Verifying...' : '🗑️ Delete'}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Report Issue Button */}
            <a
                href={`mailto:reports@thetechlads.info?subject=${encodeURIComponent('Issue Report – Attendance Web App')}&body=${encodeURIComponent(
                    `Hi,\n\nI'd like to report an issue:\n\n[Describe the issue here]\n\n--- App Details (do not edit) ---\nPlatform: Web\nURL: ${window.location.href}\nBrowser: ${navigator.userAgent}\nScreen: ${window.innerWidth}x${window.innerHeight}\nUser: ${user?.email || 'N/A'}\nTimestamp: ${new Date().toISOString()}\n`
                )}`}
                style={{
                    position: 'fixed',
                    bottom: '1.5rem',
                    right: '1.5rem',
                    background: 'rgba(255,255,255,0.08)',
                    backdropFilter: 'blur(12px)',
                    border: '1px solid rgba(255,255,255,0.15)',
                    borderRadius: '50px',
                    padding: '0.6rem 1.2rem',
                    color: 'var(--text-secondary)',
                    textDecoration: 'none',
                    fontSize: '0.85rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.4rem',
                    transition: 'all 0.2s ease',
                    zIndex: 100,
                    cursor: 'pointer'
                }}
                onMouseEnter={e => { e.currentTarget.style.background = 'rgba(129, 140, 248, 0.15)'; e.currentTarget.style.borderColor = 'rgba(129, 140, 248, 0.4)'; e.currentTarget.style.color = '#818cf8'; }}
                onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.08)'; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.15)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
            >
                🐛 Report Issue
            </a>
        </>
    );
}

export default Dashboard;
