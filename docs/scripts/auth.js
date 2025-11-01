class AuthManager {
    constructor() {
        this.passwordHash = CONFIG.PASSWORD_HASH;
    }

    async hashPassword(password) {
        const msgBuffer = new TextEncoder().encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async authenticate(password) {
        const hash = await this.hashPassword(password);
        return hash === this.passwordHash;
    }

    saveSession(password) {
        sessionStorage.setItem('reportPassword', password);
    }

    hasValidSession() {
        const savedPassword = sessionStorage.getItem('reportPassword');
        return savedPassword && this.passwordHash;
    }

    clearSession() {
        sessionStorage.removeItem('reportPassword');
    }
}
