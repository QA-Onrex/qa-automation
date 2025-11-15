// docs/scripts/auth.js
import { CONFIG } from './config.js';

export class AuthManager {
    // Renamed for clarity, but logic is the same (SHA-256)
    async hashSecret(secret) { 
        const msgBuffer = new TextEncoder().encode(secret);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    // UPDATED: Now requires two arguments, combines them for hashing
    async authenticate(username, password) {
        // 1. Combine the secrets with the space delimiter, matching the hash calculation
        const fullSecret = `${username} ${password}`; 
        
        // 2. Hash the combined secret
        const secretHash = await this.hashSecret(fullSecret);
        
        // 3. Authentication succeeds if the combined hash is correct
        return secretHash === CONFIG.FULL_SECRET_HASH;
    }

    hasValidSession() {
        // This is still correct, as the session stores the full combined secret
        return !!sessionStorage.getItem('reportPassword');
    }
}
