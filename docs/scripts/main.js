// docs/scripts/main.js

import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { setupModalCloseHandlers } from './ui_modal.js';
import { CONFIG } from './config.js';

let currentDashboardVersion = null; // Stores the last known version (timestamp)
const POLLING_INTERVAL_MS = 30000; // Check every 30 seconds (adjust as needed)

window.addEventListener('DOMContentLoaded', async () => {
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();
    window.archiveManager = new ArchiveManager();

    setupModalCloseHandlers();

    document.getElementById('login-button').addEventListener('click', handleLogin);
    
    // Handle 'Enter' key on username input (focuses on next field)
    document.getElementById('username-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') {
            e.preventDefault(); 
            document.getElementById('password-input').focus();
        }
    });

    // Handle 'Enter' key on password input (triggers login)
    document.getElementById('password-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') handleLogin();
    });

    document.getElementById('archive-dropdown').addEventListener('change', handleArchiveChange);
    document.getElementById('env-dropdown').addEventListener('change', handleEnvChange);

    if (window.authManager.hasValidSession()) {
        await showDashboardFlow();
    }
});

// --- Version Polling Functions (Kept from your snippets) ---

function startVersionPolling() {
    if (window.pollingInterval) {
        clearInterval(window.pollingInterval);
    }
    console.log('Started version polling every 30s.');
    window.pollingInterval = setInterval(checkNewVersion, POLLING_INTERVAL_MS);
}

async function checkNewVersion() {
    try {
        const response = await fetch(CONFIG.VERSION_URL, { cache: 'no-store' });
        if (!response.ok) return;
        const versionData = await response.json();
        
        // This is a timestamp, so we check if it's newer
        if (currentDashboardVersion && versionData.version > currentDashboardVersion) {
            console.log(`New version detected: ${versionData.version}. Refreshing dashboard.`);
            currentDashboardVersion = versionData.version;
            await loadDashboardData('current');
        } else if (!currentDashboardVersion) {
            // First run, just store the version
            currentDashboardVersion = versionData.version;
        }
    } catch (error) {
        console.error('Version check failed:', error);
    }
}

// --- Login Function (CRITICAL FIX HERE) ---

async function handleLogin() {
    // Assumes you have inputs: <input id="username-input"> and <input id="password-input">
    
    // 1. CRITICAL: Retrieve and trim both inputs.
    const username = document.getElementById('username-input').value.trim();
    const password = document.getElementById('password-input').value.trim();
    const errorBox = document.getElementById('error-message');

    // 2. Create the combined secret (MUST MATCH THE GITHUB SECRET AND HASH INPUT)
    const fullSecretForDecryption = `${username} ${password}`; 
    
    // 3. Authenticate using the new two-part system
    if (await window.authManager.authenticate(username, password)) { 
        
        // 4. FIX: Store the combined secret for the decryptor to use
        sessionStorage.setItem('reportPassword', fullSecretForDecryption);
        
        errorBox.style.display = 'none';
        await showDashboardFlow();
    } else {
        errorBox.style.display = 'block';
    }
}

// --- Dashboard Flow Functions (Kept from your snippets) ---

async function showDashboardFlow() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
    window.dashboardManager.showLoading();

    await window.archiveManager.loadArchiveIndex();
    window.archiveManager.populateDropdownSelector();

    // Populate fixed environment options
    window.dashboardManager.populateEnvDropdown();

    await loadDashboardData('current');
    
    // START POLLING AFTER INITIAL DATA LOAD
    startVersionPolling(); 
}

async function handleArchiveChange(event) {
    const archiveId = event.target.value;
    await loadDashboardData(archiveId);
    
    // If the user switches to an archive, stop polling
    if (window.pollingInterval && archiveId !== 'current') {
        clearInterval(window.pollingInterval);
        console.log('Stopped version polling (switched to archive view).');
    } else if (archiveId === 'current') {
        // If the user switches back to 'current', start polling again
        startVersionPolling(); 
    }
}

async function handleEnvChange() {
    window.dashboardManager.render(); // Re-render table with new filter
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
        document.getElementById('loading-message').textContent =
            'Error loading dashboard data. Please refresh or select another archive.';
    }
}
