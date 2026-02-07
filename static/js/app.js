const API_URL = '';

async function fetchData(endpoint) {
    const response = await fetch(`${API_URL}${endpoint}`);
    return await response.json();
}

async function postData(endpoint, data) {
    const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return await response.json();
}

// UI State
let currentSessionId = null;

async function loadInitialData() {
    await Promise.all([loadSessions(), loadMembers()]);
}

async function loadSessions() {
    const sessions = await fetchData('/sessions/');
    const list = document.getElementById('sessions-list');
    list.innerHTML = sessions.map(s => `
        <div class="glass-card" style="padding: 1rem; margin-bottom: 0.5rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center;" onclick="viewAttendance(${s.id}, '${s.title}')">
            <div>
                <strong>${s.title}</strong><br>
                <small>${new Date(s.date).toLocaleDateString()}</small>
            </div>
            <span class="status-badge ${s.type === 'rehearsal' ? 'status-nfc' : 'status-manual'}">${s.type}</span>
        </div>
    `).join('') || '<p>No sessions found.</p>';
}

async function loadMembers() {
    const members = await fetchData('/members/');
    const list = document.getElementById('members-list');
    list.innerHTML = members.map(m => `
        <div style="padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.05)">
            <strong>${m.name}</strong> - <small>${m.email}</small>
        </div>
    `).join('') || '<p>No members found.</p>';
}

async function viewAttendance(sessionId, title) {
    currentSessionId = sessionId;
    document.getElementById('attendance-title').innerText = `Attendance: ${title}`;
    const attendance = await fetchData(`/attendance/${sessionId}`);
    const members = await fetchData('/members/');
    const memberMap = Object.fromEntries(members.map(m => [m.id, m]));

    const content = document.getElementById('attendance-content');
    if (attendance.length === 0) {
        content.innerHTML = `
            <p>No records yet.</p>
            <div style="display:flex; gap:1rem; flex-wrap:wrap">
                ${members.map(m => `
                    <button class="btn" style="background:rgba(255,255,255,0.1)" onclick="submitAttendance(${m.id})">Mark ${m.name}</button>
                `).join('')}
            </div>
        `;
    } else {
        content.innerHTML = `
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
                    ${attendance.map(a => `
                        <tr>
                            <td>${memberMap[a.member_id]?.name || 'Unknown'}</td>
                            <td>${new Date(a.timestamp).toLocaleTimeString()}</td>
                            <td><span class="status-badge status-${a.submission_type}">${a.submission_type}</span></td>
                            <td>${a.latitude ? `${a.latitude.toFixed(4)}, ${a.longitude.toFixed(4)}` : 'N/A'}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            <div style="margin-top:2rem;">
                <h3>Mark Manual Attendance</h3>
                <div style="display:flex; gap:0.5rem; flex-wrap:wrap">
                    ${members.filter(m => !attendance.some(a => a.member_id === m.id)).map(m => `
                        <button class="btn" style="background:rgba(255,255,255,0.1)" onclick="submitAttendance(${m.id})">${m.name}</button>
                    `).join('')}
                </div>
            </div>
        `;
    }
}

async function submitAttendance(memberId) {
    if (!currentSessionId) return alert('Select a session first');

    let location = { lat: null, lng: null };

    try {
        const pos = await new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 5000 });
        });
        location.lat = pos.coords.latitude;
        location.lng = pos.coords.longitude;
    } catch (e) {
        console.warn("GPS failed, submitting without coords", e);
    }

    const res = await postData('/attendance/', {
        member_id: memberId,
        session_id: currentSessionId,
        latitude: location.lat,
        longitude: location.lng,
        submission_type: 'manual'
    });

    if (res.id) {
        viewAttendance(currentSessionId, document.getElementById('attendance-title').innerText.replace('Attendance: ', ''));
    }
}

// Modal Logic
function showModal(title, bodyHtml, onSubmit) {
    const container = document.getElementById('modal-container');
    document.getElementById('modal-title').innerText = title;
    document.getElementById('modal-body').innerHTML = bodyHtml;
    const submitBtn = document.getElementById('modal-submit');
    submitBtn.onclick = async () => {
        await onSubmit();
        hideModal();
    };
    container.style.display = 'flex';
}

function hideModal() {
    document.getElementById('modal-container').style.display = 'none';
}

function showCreateMember() {
    showModal('Add New Member', `
        <input id="new-member-name" placeholder="Full Name">
        <input id="new-member-email" placeholder="Email Address">
        <input id="new-member-nfc" placeholder="NFC ID (Optional)">
    `, async () => {
        const name = document.getElementById('new-member-name').value;
        const email = document.getElementById('new-member-email').value;
        const nfc_id = document.getElementById('new-member-nfc').value || null;
        await postData('/members/', { name, email, nfc_id });
        loadMembers();
    });
}

function showCreateSession() {
    showModal('New Session', `
        <input id="new-session-title" placeholder="Session Title (e.g. Sunday Service)">
        <select id="new-session-type">
            <option value="rehearsal">Rehearsal</option>
            <option value="program">Program</option>
        </select>
    `, async () => {
        const title = document.getElementById('new-session-title').value;
        const type = document.getElementById('new-session-type').value;
        await postData('/sessions/', { title, type, date: new Date().toISOString() });
        loadSessions();
    });
}

// Init
loadInitialData();
