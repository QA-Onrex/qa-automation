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

async function handleLogin() {
    const username = document.getElementById('username-input').value.trim();
    const password = document.getElementById('password-input').value.trim();
    const errorBox = document.getElementById('error-message');

    if (await window.authManager.authenticate(username, password)) {
        // Store the full combined secret ("username password") for decryption
        const fullSecretForDecryption = `${username} ${password}`;
        sessionStorage.setItem('reportPassword', fullSecretForDecryption);
        
        errorBox.style.display = 'none';
        await showDashboardFlow();
    } else {
        errorBox.style.display = 'block';
    }
}


// --- NEW POLLING FUNCTIONALITY ---

async function checkNewVersion() {
    // Only check if viewing the "Current (Live)" dashboard
    if (window.archiveManager.currentArchive !== 'current') {
        return;
    }

    try {
        const response = await fetch(CONFIG.VERSION_URL, {
            // Disable browser caching for the version check
            cache: 'no-store' 
        });
        if (!response.ok) {
            console.warn('Failed to fetch version file. (Possibly first run/no data)');
            return;
        }

        const versionData = await response.json();
        const newVersion = versionData.version;

        if (currentDashboardVersion === null) {
            // First time check after login/load
            currentDashboardVersion = newVersion;
        } else if (newVersion > currentDashboardVersion) {
            console.log(`New dashboard version detected: ${newVersion}. Reloading data...`);
            currentDashboardVersion = newVersion;
            
            // Reload the data and re-render the dashboard
            await loadDashboardData('current');
            // Optionally add a temporary UI notification here: 
            // document.getElementById('last-updated').textContent = 'Data automatically refreshed!';
        }
    } catch (error) {
        // This can happen if version.json hasn't been created yet
        console.error('Error during version polling:', error);
    }
}

function startVersionPolling() {
    // Stop any existing polling interval to prevent duplicates
    if (window.pollingInterval) {
        clearInterval(window.pollingInterval);
    }
    
    // Start polling the version file
    window.pollingInterval = setInterval(checkNewVersion, POLLING_INTERVAL_MS);
    console.log(`Started version polling every ${POLLING_INTERVAL_MS / 1000}s.`);
}

// --- END NEW POLLING FUNCTIONALITY ---


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
