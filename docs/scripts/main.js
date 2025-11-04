// docs/scripts/main.js
import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { setupModalCloseHandlers } from './ui_modal.js';
import { CONFIG } from './config.js';

window.addEventListener('DOMContentLoaded', async () => {
    // Initialize managers
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();
    window.archiveManager = new ArchiveManager();

    // Modal close events
    setupModalCloseHandlers();

    // Login events
    document.getElementById('login-button').addEventListener('click', handleLogin);
    document.getElementById('password-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') handleLogin();
    });

    // Archive selector
    document.getElementById('archive-dropdown').addEventListener('change', handleArchiveChange);

    // Auto-login if session already exists
    if (window.authManager.hasValidSession()) {
        await showDashboardFlow();
    }
});

async function handleLogin() {
    const password = document.getElementById('password-input').value;
    const errorBox = document.getElementById('error-message');

    if (await window.authManager.authenticate(password)) {
        sessionStorage.setItem('reportPassword', password);
        errorBox.style.display = 'none';
        await showDashboardFlow();
    } else {
        errorBox.style.display = 'block';
    }
}

async function showDashboardFlow() {
    // Switch to dashboard view
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';

    // Initial state
    window.dashboardManager.showLoading();

    // Load archives and dashboard data
    await window.archiveManager.loadArchiveIndex();
    await loadDashboardData('current');
}

async function handleArchiveChange(event) {
    const archiveId = event.target.value;
    await loadDashboardData(archiveId);
}

async function loadDashboardData(archiveId = 'current') {
    try {
        window.archiveManager.currentArchive = archiveId;
        window.dashboardManager.showLoading();

        const url = window.archiveManager.getArchiveFileName(archiveId);
        await window.dashboardManager.loadData(url);
        window.dashboardManager.render();
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        const msg = document.getElementById('loading-message');
        msg.textContent = 'Error loading dashboard data. Please refresh or select another archive.';
    }
}
