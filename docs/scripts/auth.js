// docs/scripts/auth.js
import { CONFIG } from './config.js';

export class AuthManager {
    constructor() {
        // Cached local override hash (if a local.secret file is present)
        this._localHash = null;
        this._localHashChecked = false;
    }
    // Renamed for clarity, but logic is the same (SHA-256)
    async hashSecret(secret) { 
        const msgBuffer = new TextEncoder().encode(secret);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // Try to load an optional local override secret once per session
    async loadLocalHashOnce() {
        if (this._localHashChecked) return this._localHash; // may be null
        this._localHashChecked = true;
        try {
            // A developer can create docs/scripts/local.secret (ignored from VCS) with either:
            // - a precomputed 64-char SHA-256 hex string, or
            // - the raw "username password" string to be hashed here.
            const resp = await fetch('scripts/local.secret', { cache: 'no-store' });
            if (!resp.ok) return null;
            const text = (await resp.text()).trim();
            if (!text) return null;
            const hex64 = /^[0-9a-f]{64}$/i.test(text);
            this._localHash = hex64 ? text.toLowerCase() : await this.hashSecret(text);
            return this._localHash;
        } catch (_) {
            return null;
        }
    }

    // UPDATED: Now requires two arguments, combines them for hashing
    async authenticate(username, password) {
        // 1. Combine the secrets with the space delimiter, matching the hash calculation
        const fullSecret = `${username} ${password}`; 
        
        // 2. Hash the combined secret
        const secretHash = await this.hashSecret(fullSecret);

        // Prefer a local override hash when available (for local development)
        const localHash = await this.loadLocalHashOnce();
        const expectedHash = localHash || CONFIG.FULL_SECRET_HASH;

        // 3. Authentication succeeds if the combined hash matches expected
        return secretHash === expectedHash;
    }

    hasValidSession() {
        // This is still correct, as the session stores the full combined secret
        return !!sessionStorage.getItem('reportPassword');
    }
}
