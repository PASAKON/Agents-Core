const BADGE_CLASS = { cto: 'b-cto', cmo: 'b-cmo', cfo: 'b-cfo', cxo: 'b-cxo' };

const listEl = document.getElementById('session-list');
const emptyNote = document.getElementById('empty-note');
const chipsEl = document.getElementById('role-chips');
const nameInput = document.getElementById('new-name');
const createStatus = document.getElementById('create-status');
const winTitle = document.getElementById('win-title');

let selectedRole = null;
let roles = [];

function timeAgo(ms) {
  if (!ms) return '';
  const secs = Math.max(0, Math.floor((Date.now() - ms) / 1000));
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

function renderSessions(sessions) {
  listEl.innerHTML = '';
  emptyNote.hidden = sessions.length > 0;
  winTitle.textContent = `sessions — ${sessions.length} active`;

  for (const s of sessions) {
    const a = document.createElement('a');
    a.className = 'srow';
    a.href = `/agent/${s.role}/${s.slug}`;
    a.innerHTML = `
      <span class="badge ${BADGE_CLASS[s.role] || ''}">${s.role.toUpperCase()}</span>
      <span class="slug">${s.slug}</span>
      <span class="meta">${s.attached ? '<span class="yellow">⏳</span>' : '<span class="green">✅</span>'} ${timeAgo(s.createdAt)}</span>
    `;
    listEl.appendChild(a);
  }
}

function renderChips() {
  chipsEl.innerHTML = '';
  for (const role of roles) {
    const chip = document.createElement('span');
    chip.className = 'chip' + (role === selectedRole ? ' on' : '');
    chip.textContent = role.toUpperCase();
    chip.addEventListener('click', () => {
      selectedRole = role;
      renderChips();
    });
    chipsEl.appendChild(chip);
  }
}

async function loadSessions() {
  const res = await fetch('/api/sessions');
  if (res.status === 401) return (window.location.href = '/login');
  const data = await res.json();
  roles = data.roles || [];
  if (!selectedRole) selectedRole = roles[0] || null;
  renderChips();
  renderSessions(data.sessions || []);
}

async function handleCreate() {
  if (!selectedRole) return;
  createStatus.className = 'status-line';
  createStatus.textContent = 'creating…';
  try {
    const res = await fetch('/api/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: selectedRole, name: nameInput.value.trim() }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || 'create failed');
    window.location.href = data.url;
  } catch (err) {
    createStatus.className = 'status-line err';
    createStatus.textContent = err.message;
  }
}

async function handleLogout() {
  await fetch('/api/auth/logout', { method: 'POST' });
  window.location.href = '/login';
}

document.getElementById('btn-create').addEventListener('click', handleCreate);
document.getElementById('btn-logout').addEventListener('click', handleLogout);

loadSessions();
setInterval(loadSessions, 5000);
