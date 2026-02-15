import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchMembers, addMember, updateMember } from '../store/membersSlice';
import Modal from '../components/Modal';

const ROLES = ['soprano', 'alto', 'tenor', 'bass', 'bass_guitar', 'keyboard', 'drums', 'electric_guitar'];
const PERMISSIONS = ['admin', 'editor', 'member'];

function MembersManagement() {
    const dispatch = useDispatch();
    const { items: members, loading } = useSelector(state => state.members);
    const [isAddModalOpen, setIsAddModalOpen] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [editingMember, setEditingMember] = useState(null);
    const [newMember, setNewMember] = useState({
        first_name: '',
        last_name: '',
        email: '',
        phone_number: '',
        password: '',
        roles: [],
        nfc_id: ''
    });

    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        dispatch(fetchMembers());
    }, [dispatch]);

    const filteredMembers = members.filter(m =>
        (m.first_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (m.last_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (m.email || '').toLowerCase().includes(searchQuery.toLowerCase())
    );

    const handleAddMember = () => {
        dispatch(addMember({
            ...newMember,
            first_name: newMember.first_name.trim(),
            last_name: newMember.last_name.trim(),
            email: newMember.email.trim(),
            phone_number: newMember.phone_number.trim(),
            nfc_id: newMember.nfc_id.trim(),
            password: newMember.password.trim()
        }));
        setIsAddModalOpen(false);
        setNewMember({
            first_name: '',
            last_name: '',
            email: '',
            phone_number: '',
            password: '',
            roles: [],
            nfc_id: ''
        });
    };

    const openEditModal = (member) => {
        setEditingMember({
            id: member.id,
            first_name: member.first_name,
            last_name: member.last_name,
            email: member.email,
            phone_number: member.phone_number || '',
            nfc_id: member.nfc_id || '',
            roles: member.roles || [],
            permissions: member.permissions || ['member']
        });
        setIsEditModalOpen(true);
    };

    const handleUpdateMember = () => {
        if (!editingMember) return;
        dispatch(updateMember({
            id: editingMember.id,
            updates: {
                first_name: editingMember.first_name.trim(),
                last_name: editingMember.last_name.trim(),
                email: editingMember.email.trim(),
                phone_number: (editingMember.phone_number || '').trim() || null,
                nfc_id: (editingMember.nfc_id || '').trim() || null,
                roles: editingMember.roles,
                permissions: editingMember.permissions
            }
        }));
        setIsEditModalOpen(false);
        setEditingMember(null);
    };

    const toggleNewMemberRole = (role) => {
        setNewMember(prev => ({
            ...prev,
            roles: prev.roles.includes(role)
                ? prev.roles.filter(r => r !== role)
                : [...prev.roles, role]
        }));
    };

    const toggleEditRole = (role) => {
        setEditingMember(prev => ({
            ...prev,
            roles: prev.roles.includes(role)
                ? prev.roles.filter(r => r !== role)
                : [...prev.roles, role]
        }));
    };

    const toggleEditPermission = (perm) => {
        setEditingMember(prev => ({
            ...prev,
            permissions: prev.permissions.includes(perm)
                ? prev.permissions.filter(p => p !== perm)
                : [...prev.permissions, perm]
        }));
    };

    return (
        <div className="glass-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <h1 style={{ margin: 0 }}>Member Management</h1>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <input
                        type="text"
                        placeholder="Search members..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '8px',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'var(--text-primary)',
                            width: '250px',
                            marginBottom: 0
                        }}
                    />
                    <button className="btn" onClick={() => setIsAddModalOpen(true)}>+ Add Member</button>
                </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table>
                    <thead>
                        <tr>
                            <th>Name</th>
                            <th>Email</th>
                            <th>Phone</th>
                            <th>Roles</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {filteredMembers.map(m => (
                            <tr key={m.id}>
                                <td>{m.first_name} {m.last_name}</td>
                                <td>{m.email}</td>
                                <td>{m.phone_number || 'N/A'}</td>
                                <td>
                                    <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                                        {m.roles?.map(r => (
                                            <span key={r} className="status-badge" style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#6366f1', fontSize: '0.75rem' }}>{r}</span>
                                        ))}
                                    </div>
                                </td>
                                <td>
                                    <span className={`status-badge ${m.email_verified || m.phone_number_verified ? 'status-manual' : 'status-nfc'}`}>
                                        {m.email_verified || m.phone_number_verified ? 'Verified' : 'Unverified'}
                                    </span>
                                </td>
                                <td>
                                    <button className="btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }} onClick={() => openEditModal(m)}>Edit</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Add Member Modal */}
            <Modal title="Add New Member" isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} onSubmit={handleAddMember}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                    <input placeholder="First Name" value={newMember.first_name} onChange={e => setNewMember({ ...newMember, first_name: e.target.value })} />
                    <input placeholder="Last Name" value={newMember.last_name} onChange={e => setNewMember({ ...newMember, last_name: e.target.value })} />
                </div>
                <input placeholder="Email Address" value={newMember.email} onChange={e => setNewMember({ ...newMember, email: e.target.value })} />
                <input placeholder="Phone (e.g. +1234567890)" value={newMember.phone_number} onChange={e => setNewMember({ ...newMember, phone_number: e.target.value })} />
                <input type="password" placeholder="Password" value={newMember.password} onChange={e => setNewMember({ ...newMember, password: e.target.value })} />
                <input placeholder="NFC ID (Optional)" value={newMember.nfc_id} onChange={e => setNewMember({ ...newMember, nfc_id: e.target.value })} />

                <p style={{ margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Roles</p>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                    {ROLES.map(role => (
                        <button
                            key={role}
                            type="button"
                            className="status-badge"
                            style={{
                                cursor: 'pointer',
                                border: 'none',
                                background: newMember.roles.includes(role) ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)',
                                color: newMember.roles.includes(role) ? 'white' : 'var(--text-secondary)'
                            }}
                            onClick={() => toggleNewMemberRole(role)}
                        >
                            {role}
                        </button>
                    ))}
                </div>
            </Modal>

            {/* Edit Member Modal */}
            <Modal title="Edit Member" isOpen={isEditModalOpen} onClose={() => { setIsEditModalOpen(false); setEditingMember(null); }} onSubmit={handleUpdateMember}>
                {editingMember && (
                    <>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                            <input placeholder="First Name" value={editingMember.first_name} onChange={e => setEditingMember({ ...editingMember, first_name: e.target.value })} />
                            <input placeholder="Last Name" value={editingMember.last_name} onChange={e => setEditingMember({ ...editingMember, last_name: e.target.value })} />
                        </div>
                        <input placeholder="Email Address" value={editingMember.email} onChange={e => setEditingMember({ ...editingMember, email: e.target.value })} />
                        <input placeholder="Phone (e.g. +1234567890)" value={editingMember.phone_number} onChange={e => setEditingMember({ ...editingMember, phone_number: e.target.value })} />
                        <input placeholder="NFC ID (Optional)" value={editingMember.nfc_id} onChange={e => setEditingMember({ ...editingMember, nfc_id: e.target.value })} />

                        <p style={{ margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Roles</p>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                            {ROLES.map(role => (
                                <button
                                    key={role}
                                    type="button"
                                    className="status-badge"
                                    style={{
                                        cursor: 'pointer',
                                        border: 'none',
                                        background: editingMember.roles.includes(role) ? 'var(--primary-color)' : 'rgba(255,255,255,0.05)',
                                        color: editingMember.roles.includes(role) ? 'white' : 'var(--text-secondary)'
                                    }}
                                    onClick={() => toggleEditRole(role)}
                                >
                                    {role}
                                </button>
                            ))}
                        </div>

                        <p style={{ margin: '1rem 0 0.5rem', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Permissions</p>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                            {PERMISSIONS.map(perm => (
                                <button
                                    key={perm}
                                    type="button"
                                    className="status-badge"
                                    style={{
                                        cursor: 'pointer',
                                        border: 'none',
                                        background: editingMember.permissions.includes(perm) ? 'var(--accent-color)' : 'rgba(255,255,255,0.05)',
                                        color: editingMember.permissions.includes(perm) ? 'white' : 'var(--text-secondary)'
                                    }}
                                    onClick={() => toggleEditPermission(perm)}
                                >
                                    {perm}
                                </button>
                            ))}
                        </div>
                    </>
                )}
            </Modal>
        </div>
    );
}

export default MembersManagement;
