import React from 'react';

const Modal = ({ title, isOpen, onClose, onSubmit, children }) => {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="glass-card" style={{ maxWidth: '500px', width: '100%', margin: 0 }}>
                <h2>{title}</h2>
                <div>{children}</div>
                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '1rem', marginTop: '1rem' }}>
                    <button className="btn" style={{ background: 'transparent', border: '1px solid var(--text-secondary)' }} onClick={onClose}>Cancel</button>
                    <button className="btn" onClick={onSubmit}>Submit</button>
                </div>
            </div>
        </div>
    );
};

export default Modal;
