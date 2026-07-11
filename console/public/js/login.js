const usernameInput = document.getElementById('username');
const totpInput = document.getElementById('totp-token');
const statusEl = document.getElementById('status');
const bootstrapNote = document.getElementById('bootstrap-note');
const passkeyLabel = document.getElementById('passkey-label');

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = 'status-line' + (kind ? ' ' + kind : '');
}

async function apiPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function fetchStatus() {
  const res = await fetch('/api/auth/status');
  return res.json();
}

async function refreshBootstrapNote() {
  try {
    const status = await fetchStatus();
    bootstrapNote.hidden = !status.bootstrap;
    passkeyLabel.textContent = status.bootstrap
      ? 'Register this device (Face ID / Passkey)'
      : 'Sign in with Face ID / Passkey';
  } catch {
    // non-fatal — status pill just won't update
  }
}

async function handlePasskey() {
  if (!window.SimpleWebAuthnBrowser || !window.SimpleWebAuthnBrowser.browserSupportsWebAuthn()) {
    setStatus('this browser does not support passkeys — use TOTP fallback', 'err');
    return;
  }
  const username = usernameInput.value.trim();
  if (!username) return setStatus('enter operator name first', 'err');

  setStatus('waiting for Face ID / passkey…', '');
  try {
    const status = await fetchStatus();
    if (status.bootstrap) {
      const options = await apiPost('/api/auth/webauthn/register-options', { username });
      const attResp = await window.SimpleWebAuthnBrowser.startRegistration({ optionsJSON: options });
      await apiPost('/api/auth/webauthn/register-verify', { username, response: attResp });
    } else {
      const options = await apiPost('/api/auth/webauthn/login-options', { username });
      const authResp = await window.SimpleWebAuthnBrowser.startAuthentication({ optionsJSON: options });
      await apiPost('/api/auth/webauthn/login-verify', { username, response: authResp });
    }
    setStatus('signed in — redirecting…', 'ok');
    window.location.href = '/';
  } catch (err) {
    setStatus(err.message || 'passkey flow failed', 'err');
  }
}

async function handleTotpVerify() {
  const username = usernameInput.value.trim();
  const token = totpInput.value.trim();
  if (!username || !token) return setStatus('enter operator + 6-digit code', 'err');

  setStatus('verifying…', '');
  try {
    await apiPost('/api/auth/totp/verify', { username, token });
    setStatus('signed in — redirecting…', 'ok');
    window.location.href = '/';
  } catch (err) {
    setStatus(err.message || 'TOTP verify failed', 'err');
  }
}

async function handleSetupTotp() {
  const username = usernameInput.value.trim();
  if (!username) return setStatus('enter operator name first', 'err');
  setStatus('generating TOTP secret…', '');
  try {
    const { secret, uri } = await apiPost('/api/auth/totp/setup', { username });
    setStatus(`TOTP secret: ${secret} — add to an authenticator app, then enter a code above.`, 'ok');
    console.log('[console] TOTP provisioning URI:', uri);
  } catch (err) {
    setStatus(err.message || 'TOTP setup failed', 'err');
  }
}

document.getElementById('btn-passkey').addEventListener('click', handlePasskey);
document.getElementById('btn-totp').addEventListener('click', handleTotpVerify);
document.getElementById('btn-setup-totp').addEventListener('click', handleSetupTotp);

refreshBootstrapNote();
