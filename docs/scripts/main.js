// Main application entry point
class QAAutomationApp {
    constructor() {
        this.authManager = new AuthManager();
        this.dashboard = new Dashboard();
        this.tooltipManager = new TooltipManager();
        this.modalManager = new ModalManager();
        this.cryptoManager = new CryptoManager();
    }

    async initialize() {
        this.setupEventListeners();
        await this.checkExistingSession();
    }

    setupEventListeners() {
        document.getElementById('login-button').addEventListener('click', () => this.handleLogin());
        document.getElementById('password-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });
    }

    async handleLogin() {
        const password = document.getElementById('password-input').value;
        
        if (await this.authManager.authenticate(password)) {
            this.authManager.saveSession(password);
            this.showDashboard();
            await this.loadDashboardData();
        } else {
            document.getElementById('error-message').style.display = 'block';
        }
    }

    async checkExistingSession() {
        if (this.authManager.hasValidSession()) {
            this.showDashboard();
            await this.loadDashboardData();
        } else if (!CONFIG.PASSWORD_HASH) {
            // No password protection required
            this.showDashboard();
            await this.loadDashboardData();
        }
    }

    async loadDashboardData() {
        try {
            this.dashboard.showLoading();
            await this.dashboard.loadData();
            this.dashboard.render();
        } catch (error) {
            document.getElementById('loading-message').innerHTML = 
                'Error loading dashboard data. Please try refreshing the page.';
        }
    }

    showDashboard() {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', async () => {
    window.app = new QAAutomationApp();
    await window.app.initialize();
});
