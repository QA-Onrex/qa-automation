// docs/scripts/decryptor.js

/**
 * Decrypt encrypted byte array (Uint8Array) using password.
 * Format: [16 bytes salt][12 bytes nonce][rest ciphertext]
 */
async function decryptAES(encryptedBytes, password) {
  if (!(encryptedBytes instanceof Uint8Array)) {
    throw new Error('decryptAES expects Uint8Array');
  }
  if (encryptedBytes.length < 28) {
    throw new Error('Encrypted data too short');
  }

  const salt = encryptedBytes.slice(0, 16);
  const nonce = encryptedBytes.slice(16, 28);
  const ciphertext = encryptedBytes.slice(28);

  const enc = new TextEncoder();
  const baseKey = await crypto.subtle.importKey(
    'raw',
    enc.encode(password),
    { name: 'PBKDF2' },
    false,
    ['deriveKey']
  );

  const key = await crypto.subtle.deriveKey(
    { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
    baseKey,
    { name: 'AES-GCM', length: 256 },
    false,
    ['decrypt']
  );

  const plain = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, key, ciphertext);
  return new Uint8Array(plain);
}

/**
 * Open a report (session) - fetches base64 content from netlify_url,
 * decodes base64 -> Uint8Array, decrypts using stored password and opens a new tab.
 *
 * session: object must contain .netlify_url (string)
 */
export async function openReport(session) {
  if (!session || !session.netlify_url) {
    alert('Report URL missing');
    return;
  }

  if (window.archiveManager?.currentArchive !== 'current') {
    alert('Detailed reports are only available for Current (Live) data. Switch to Current to open reports.');
    return;
  }

  const password = sessionStorage.getItem('reportPassword');
  if (!password) {
    alert('Password missing. Please login.');
    return;
  }

  try {
    const resp = await fetch(session.netlify_url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const base64Text = await resp.text();
    // base64Text might contain whitespace/newlines — atob handles that
    const binary = atob(base64Text);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

    const decrypted = await decryptAES(bytes, password);
    const decoded = new TextDecoder().decode(decrypted);
    const blob = new Blob([decoded], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
  } catch (err) {
    console.error('openReport failed', err);
    alert('Failed to open report — check console for details.');
  }
}
