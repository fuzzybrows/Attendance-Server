import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchMembers, addMember } from './store/membersSlice';
import { fetchSessions, addSession, setCurrentSession } from './store/sessionsSlice';
import { fetchAttendance, submitAttendance } from './store/attendanceSlice';
import Modal from './components/Modal';

function Dashboard() {
    const dispatch = useDispatch();
    const { items: members } = useSelector(state => state.members);
    const { items: sessions, currentSession } = useSelector(state => state.sessions);
    const { items: attendance } = useSelector(state => state.attendance);

    const [isMemberModalOpen, setMemberModalOpen] = useState(false);
    const [isSessionModalOpen, setSessionModalOpen] = useState(false);

    const [newMember, setNewMember] = useState({ name: '', email: '', nfc_id: '' });
    const [newSession, setNewSession] = useState({ title: '', type: 'rehearsal' });

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
        dispatch(addMember(newMember));
        setMemberModalOpen(false);
        setNewMember({ name: '', email: '', nfc_id: '' });
    };

    const handleAddSession = () => {
        dispatch(addSession({ ...newSession, date: new Date().toISOString() }));
        setSessionModalOpen(false);
        setNewSession({ title: '', type: 'rehearsal' });
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
            submission_type: 'manual'
        }));
    };

    return (
        <>
            <div className="grid">
                <div className="glass-card">
                    <h2>Active Sessions</h2>
                    <div id="sessions-list">
                        {sessions.map(s => (
                            <div key={s.id} className="glass-card" style={{ padding: '1rem', marginBottom: '0.5rem', cursor: 'pointer', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }} onClick={() => dispatch(setCurrentSession(s))}>
                                <div>
                                    <strong>{s.title}</strong><br />
                                    <small>{new Date(s.date).toLocaleDateString()}</small>
                                </div>
                                <span className={`status-badge ${s.type === 'rehearsal' ? 'status-nfc' : 'status-manual'}`}>{s.type}</span>
                            </div>
                        ))}
                    </div>
                    <button className="btn" onClick={() => setSessionModalOpen(true)}>+ New Session</button>
                </div>

                <div className="glass-card">
                    <h2>Members</h2>
                    <div id="members-list">
                        {members.map(m => (
                            <div key={m.id} style={{ padding: '0.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                <strong>{m.name}</strong> - <small>{m.email}</small>
                            </div>
                        ))}
                    </div>
                    <button className="btn" onClick={() => setMemberModalOpen(true)}>+ Add Member</button>
                </div>
            </div>

            <div className="glass-card">
                <h2>{currentSession ? `Attendance: ${currentSession.title}` : 'Attendance Records'}</h2>
                {!currentSession ? (
                    <p>Select a session to view attendance.</p>
                ) : (
                    <div>
                        <table>
                            <thead>
                                <tr>
                                    <th>Member</th>
                                    <th>Time</th>
                                    <th>Type</th>
                                    <th>Location</th>
                                </tr>
                            </thead>
                            <tbody>
                                {attendance.map(a => (
                                    <tr key={a.id}>
                                        <td>{members.find(m => m.id === a.member_id)?.name || 'Unknown'}</td>
                                        <td>{new Date(a.timestamp).toLocaleTimeString()}</td>
                                        <td><span className={`status-badge status-${a.submission_type}`}>{a.submission_type}</span></td>
                                        <td>{a.latitude ? `${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}` : 'N/A'}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        <div style={{ marginTop: '2rem' }}>
                            <h3>Mark Manual Attendance</h3>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {members.filter(m => !attendance.some(a => a.member_id === m.id)).map(m => (
                                    <button key={m.id} className="btn" style={{ background: 'rgba(255,255,255,0.1)' }} onClick={() => handleMarkAttendance(m.id)}>
                                        {m.name}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Modal title="Add New Member" isOpen={isMemberModalOpen} onClose={() => setMemberModalOpen(false)} onSubmit={handleAddMember}>
                <input placeholder="Full Name" value={newMember.name} onChange={e => setNewMember({ ...newMember, name: e.target.value })} />
                <input placeholder="Email Address" value={newMember.email} onChange={e => setNewMember({ ...newMember, email: e.target.value })} />
                <input placeholder="NFC ID (Optional)" value={newMember.nfc_id} onChange={e => setNewMember({ ...newMember, nfc_id: e.target.value })} />
            </Modal>

            <Modal title="New Session" isOpen={isSessionModalOpen} onClose={() => setSessionModalOpen(false)} onSubmit={handleAddSession}>
                <input placeholder="Session Title" value={newSession.title} onChange={e => setNewSession({ ...newSession, title: e.target.value })} />
                <select value={newSession.type} onChange={e => setNewSession({ ...newSession, type: e.target.value })}>
                    <option value="rehearsal">Rehearsal</option>
                    <option value="program">Program</option>
                </select>
            </Modal>
        </>
    );
}

export default Dashboard;
