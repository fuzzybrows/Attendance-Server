import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { fetchSessions, deleteSession, bulkDeleteSessions, updateSessionStatus, setCurrentSession } from '../store/sessionsSlice';
import axios from 'axios';

const statusColors = {
    active: { bg: 'rgba(74, 222, 128, 0.15)', border: 'rgba(74, 222, 128, 0.4)', color: '#4ade80' },
    concluded: { bg: 'rgba(251, 191, 36, 0.15)', border: 'rgba(251, 191, 36, 0.4)', color: '#fbbf24' },
    archived: { bg: 'rgba(148, 163, 184, 0.15)', border: 'rgba(148, 163, 184, 0.4)', color: '#94a3b8' },
};

function Sessions() {
    const dispatch = useDispatch();
    const navigate = useNavigate();
    const { items: sessions } = useSelector(state => state.sessions);
    const { user } = useSelector(state => state.auth);
    const isAdmin = user?.permissions?.includes('admin');

    const [searchQuery, setSearchQuery] = useState('');
    const [statusFilter, setStatusFilter] = useState('all');
    const [selected, setSelected] = useState(new Set());

    // Delete state
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [deletePassword, setDeletePassword] = useState('');
    const [deleteError, setDeleteError] = useState('');
    const [deleteLoading, setDeleteLoading] = useState(false);

    useEffect(() => {
        dispatch(fetchSessions());
    }, [dispatch]);

    // Redirect non-admin
    useEffect(() => {
        if (!isAdmin) {
            navigate('/');
        }
    }, [isAdmin, navigate]);

    if (!isAdmin) return null;

    // Fuzzy search: case-insensitive substring match on title, type, status
    const fuzzyMatch = (session) => {
        if (!searchQuery.trim()) return true;
        const q = searchQuery.toLowerCase();
        return (
            (session.title || '').toLowerCase().includes(q) ||
            (session.type || '').toLowerCase().includes(q) ||
            (session.status || 'active').toLowerCase().includes(q)
        );
    };

    const filtered = sessions
        .filter(fuzzyMatch)
        .filter(s => statusFilter === 'all' || (s.status || 'active') === statusFilter);

    const grouped = {
        active: filtered.filter(s => (s.status || 'active') === 'active'),
        concluded: filtered.filter(s => s.status === 'concluded'),
        archived: filtered.filter(s => s.status === 'archived'),
    };

    const handleStatusChange = (sessionId, newStatus) => {
        dispatch(updateSessionStatus({ id: sessionId, status: newStatus }));
    };

    const requestDelete = (sessionId, label) => {
        setDeleteTarget({ id: sessionId, label });
        setDeletePassword('');
        setDeleteError('');
    };

    const requestBulkDelete = () => {
        setDeleteTarget({ bulk: true, ids: [...selected], label: `${selected.size} session${selected.size > 1 ? 's' : ''}` });
        setDeletePassword('');
        setDeleteError('');
    };

    const handleConfirmDelete = async () => {
        setDeleteLoading(true);
        try {
            const response = await axios.post('/auth/login', { login: user.email, password: deletePassword });
            if (response.data.access_token) {
                if (deleteTarget.bulk) {
                    await dispatch(bulkDeleteSessions(deleteTarget.ids)).unwrap();
                    setSelected(new Set());
                } else {
                    await dispatch(deleteSession(deleteTarget.id)).unwrap();
                }
                setDeleteTarget(null);
            }
        } catch (err) {
            setDeleteError(err.response?.status === 401 ? 'Invalid password' : 'Error verifying password');
        } finally {
            setDeleteLoading(false);
        }
    };

    const handleViewAttendance = (session) => {
        dispatch(setCurrentSession(session));
        navigate('/');
    };

    const renderGroup = (title, items, statusKey) => {
        if (items.length === 0) return null;
        const sc = statusColors[statusKey];
        return (
            <div key={statusKey} style={{ marginBottom: '2rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                    <h3 style={{ margin: 0 }}>{title}</h3>
                    <span style={{
                        background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color,
                        padding: '0.15rem 0.6rem', borderRadius: '12px', fontSize: '0.8rem', fontWeight: 600
                    }}>
                        {items.length}
                    </span>
                </div>
                {items.map(s => (
                    <div key={s.id} className="glass-card" style={{
                        padding: '1rem', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                        border: selected.has(s.id) ? '1px solid rgba(129, 140, 248, 0.4)' : `1px solid ${sc.border}`,
                        cursor: 'pointer', transition: 'all 0.2s ease'
                    }}
                        onClick={() => handleViewAttendance(s)}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <input
                                type="checkbox"
                                checked={selected.has(s.id)}
                                onChange={(e) => {
                                    e.stopPropagation();
                                    const next = new Set(selected);
                                    if (e.target.checked) next.add(s.id);
                                    else next.delete(s.id);
                                    setSelected(next);
                                }}
                                onClick={(e) => e.stopPropagation()}
                                style={{ accentColor: '#818cf8' }}
                            />
                            <div>
                                <strong>{s.title}</strong><br />
                                <small style={{ color: 'var(--text-secondary)' }}>{new Date(s.start_time).toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' })}</small>
                            </div>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <span className={`status-badge ${s.type === 'rehearsal' ? 'status-nfc' : 'status-manual'}`}>{s.type}</span>
                            <select
                                value={s.status || 'active'}
                                onChange={(e) => { e.stopPropagation(); handleStatusChange(s.id, e.target.value); }}
                                onClick={(e) => e.stopPropagation()}
                                style={{
                                    background: sc.bg, border: `1px solid ${sc.border}`, color: sc.color,
                                    borderRadius: '8px', padding: '0.2rem 0.4rem', fontSize: '0.8rem', cursor: 'pointer', outline: 'none'
                                }}
                            >
                                <option value="active">Active</option>
                                <option value="concluded">Concluded</option>
                                <option value="archived">Archived</option>
                            </select>
                            <button
                                className="btn"
                                style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
                                onClick={(e) => { e.stopPropagation(); requestDelete(s.id, s.title); }}
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <>
            <div className="glass-card" style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.75rem' }}>
                    <h2 style={{ margin: 0 }}>All Sessions</h2>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        {selected.size > 0 && (
                            <button
                                className="btn"
                                style={{ background: 'rgba(255,50,50,0.2)', border: '1px solid rgba(255,50,50,0.4)', color: '#ff6b6b', padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}
                                onClick={requestBulkDelete}
                            >
                                🗑️ Delete {selected.size} selected
                            </button>
                        )}
                    </div>
                </div>

                {/* Search & Filter Bar */}
                <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
                    <input
                        type="text"
                        placeholder="🔍 Search sessions by title, type, or status..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            flex: 1, minWidth: '200px', padding: '0.6rem 1rem', borderRadius: '10px',
                            background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.15)',
                            color: 'var(--text-primary)', fontSize: '0.9rem', outline: 'none',
                            transition: 'border-color 0.2s ease'
                        }}
                        onFocus={(e) => e.target.style.borderColor = 'rgba(129, 140, 248, 0.5)'}
                        onBlur={(e) => e.target.style.borderColor = 'rgba(255,255,255,0.15)'}
                    />
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                        {['all', 'active', 'concluded', 'archived'].map(f => (
                            <button
                                key={f}
                                className="btn"
                                onClick={() => setStatusFilter(f)}
                                style={{
                                    padding: '0.4rem 0.8rem', fontSize: '0.8rem',
                                    background: statusFilter === f ? 'rgba(129, 140, 248, 0.2)' : 'rgba(255,255,255,0.05)',
                                    border: statusFilter === f ? '1px solid rgba(129, 140, 248, 0.4)' : '1px solid rgba(255,255,255,0.15)',
                                    color: statusFilter === f ? '#818cf8' : 'var(--text-secondary)',
                                    borderRadius: '8px', textTransform: 'capitalize'
                                }}
                            >
                                {f}
                            </button>
                        ))}
                    </div>
                </div>

                {filtered.length === 0 ? (
                    <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                        {searchQuery ? `No sessions matching "${searchQuery}"` : 'No sessions found.'}
                    </p>
                ) : (
                    <>
                        {renderGroup('🟢 Active', grouped.active, 'active')}
                        {renderGroup('🟡 Concluded', grouped.concluded, 'concluded')}
                        {renderGroup('⚪ Archived', grouped.archived, 'archived')}
                    </>
                )}
            </div>

            {/* Delete Confirmation Modal */}
            {deleteTarget && (
                <div className="modal-overlay">
                    <div className="glass-card" style={{ maxWidth: '420px', width: '100%', margin: 0 }}>
                        <h2 style={{ color: '#ff6b6b' }}>⚠️ Confirm Delete</h2>
                        <p>
                            You are about to delete: <strong>{deleteTarget.label}</strong>
                        </p>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                            This will also delete all attendance records for {deleteTarget.bulk ? 'these sessions' : 'this session'}.
                        </p>
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
        </>
    );
}

export default Sessions;
