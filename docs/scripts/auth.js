// docs/scripts/auth.js
import { CONFIG } from './config.js';

export class AuthManager {
    async hashPassword(password) {
        const msgBuffer = new TextEncoder().encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async authenticate(password) {
        const hash = await this.hashPassword(password);
        return hash === CONFIG.PASSWORD_HASH;
    }

    hasValidSession() {
        return !!sessionStorage.getItem('reportPassword');
    }
}
