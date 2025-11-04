// docs/scripts/decryptor.js

export async function openReport(session) {
    if (window.archiveManager.currentArchive !== 'current') {
        alert('Reports are only available for Current (Live) data.');
        return;
    }

    const password = sessionStorage.getItem('reportPassword');
    if (!password) {
        alert('Password missing.');
        return;
    }

    try {
        const response = await fetch(session.netlify_url);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const base64 = await response.text();
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        const decryptedBytes = await decryptAES(bytes, password);
        const text = new TextDecoder().decode(decryptedBytes);
        const blob = new Blob([text], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (err) {
        console.error('Decryption failed:', err);
        alert('Failed to decrypt report. Check console for details.');
    }
}

async function decryptAES(encrypted, password) {
    const salt = encrypted.slice(0, 16);
    const nonce = encrypted.slice(16, 28);
    const ciphertext = encrypted.slice(28);

    const keyMaterial = await crypto.subtle.importKey('raw', new TextEncoder().encode(password), { name: 'PBKDF2' }, false, ['deriveKey']);
    const key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' },
        keyMaterial,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
    );

    const decrypted = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: nonce }, key, ciphertext);
    return new Uint8Array(decrypted);
}
