// docs/scripts/main.js
import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';

window.addEventListener('DOMContentLoaded', async () => {
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();
    window.archiveManager = new ArchiveManager();

    document.getElementById('login-button').addEventListener('click', handleLogin);
    document.getElementById('password-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') handleLogin();
    });

    document.getElementById('archive-dropdown').addEventListener('change', handleArchiveChange);

    if (window.authManager.hasValidSession()) {
        await showDashboardFlow();
    }
});

async function handleLogin() {
    const password = document.getElementById('password-input').value;
    if (await window.authManager.authenticate(password)) {
        sessionStorage.setItem('reportPassword', password);
        await showDashboardFlow();
    } else {
        document.getElementById('error-message').style.display = 'block';
    }
}

async function showDashboardFlow() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
    window.dashboardManager.showLoading();
    await window.archiveManager.loadArchiveIndex();
    await window.dashboardManager.loadData();
    window.dashboardManager.render();
}

async function handleArchiveChange(e) {
    const archiveId = e.target.value;
    const url = window.archiveManager.getArchiveFileName(archiveId);
    window.dashboardManager.showLoading();
    await window.dashboardManager.loadData(url);
    window.dashboardManager.render();
}
