// docs/scripts/main.js

import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { TimelineManager } from './timeline.js';
import { setupModalCloseHandlers } from './modal.js';
import { CONFIG } from './config.js';

let currentDashboardVersion = null; 
const POLLING_INTERVAL_MS = 30000; 
let mailboxPollTimer = null;
let lastWorkflowTriggerTs = 0;

// Initialize global managers
window.authManager = new AuthManager();
window.dashboardManager = new DashboardManager();
window.archiveManager = new ArchiveManager();
window.timelineManager = new TimelineManager();

window.addEventListener('DOMContentLoaded', async () => {
    setupModalCloseHandlers();

    document.getElementById('login-button').addEventListener('click', handleLogin);
    
    document.getElementById('username-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') {
            e.preventDefault(); 
            document.getElementById('password-input').focus();
        }
    });

    document.getElementById('password-input').addEventListener('keypress', e => {
        if (e.key === 'Enter') handleLogin();
    });

    document.getElementById('archive-dropdown').addEventListener('change', handleArchiveChange);
    
    document.getElementById('env-dropdown').addEventListener('change', () => {
        handleEnvChange(); 
        window.timelineManager.renderTimeline(); 
    });

    if (window.authManager.hasValidSession()) {
        await showDashboardFlow();
    }
});

// --- Version Polling Functions ---

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
        
        if (currentDashboardVersion && versionData.version > currentDashboardVersion) {
            console.log(`New version detected: ${versionData.version}. Refreshing dashboard.`);
            currentDashboardVersion = versionData.version;
            await loadDashboardData('current');
            window.timelineManager.renderTimeline(); 
        } else if (!currentDashboardVersion) {
            currentDashboardVersion = versionData.version;
        }
    } catch (error) {
        console.error('Version check failed:', error);
    }
}

// --- Mailbox Polling + Workflow Trigger ---
function startMailboxPolling() {
    if (!CONFIG.AUTO_MAILBOX_POLL_ENABLED) return;
    if (mailboxPollTimer) clearInterval(mailboxPollTimer);
    const interval = CONFIG.MAILBOX_POLL_INTERVAL_MS || 60000;
    console.log(`Mailbox polling enabled: every ${Math.round(interval/1000)}s`);
    mailboxPollTimer = setInterval(checkMailboxAndTrigger, interval);
}

function stopMailboxPolling() {
    if (mailboxPollTimer) {
        clearInterval(mailboxPollTimer);
        mailboxPollTimer = null;
        console.log('Mailbox polling stopped.');
    }
}

async function checkMailboxAndTrigger() {
    try {
        // Only poll when viewing Current (Live)
        if (window.archiveManager?.currentArchive !== 'current') return;

        const pollUrl = CONFIG.MAILBOX_POLL_URL;
        const resp = await fetch(pollUrl, { cache: 'no-store' });
        if (!resp.ok) return;
        const data = await resp.json();
        if (data && data.found) {
            const now = Date.now();
            const cooldown = CONFIG.WORKFLOW_COOLDOWN_MS || (10 * 60 * 1000);
            if (now - lastWorkflowTriggerTs < cooldown) {
                console.log('New report detected but still in cooldown window. Skipping trigger.');
                return;
            }
            lastWorkflowTriggerTs = now;
            console.log('New report detected. Triggering workflow...');
            try {
                const triggerResp = await fetch(CONFIG.WORKFLOW_TRIGGER_URL, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ reason: 'auto-detected-new-report', ts: now })
                });
                if (!triggerResp.ok) {
                    console.warn('Workflow trigger request failed:', triggerResp.status);
                }
            } catch (e) {
                console.error('Failed to call workflow trigger endpoint:', e);
            }
        }
    } catch (e) {
        console.error('Mailbox poll failed:', e);
    }
}

// --- Login Function ---

async function handleLogin() {
    const username = document.getElementById('username-input').value.trim();
    const password = document.getElementById('password-input').value.trim();
    const errorBox = document.getElementById('error-message');
    const fullSecretForDecryption = `${username} ${password}`; 
    
    if (await window.authManager.authenticate(username, password)) { 
        sessionStorage.setItem('reportPassword', fullSecretForDecryption);
        errorBox.style.display = 'none';
        await showDashboardFlow();
    } else {
        errorBox.style.display = 'block';
    }
}

// --- Dashboard Flow Functions ---

async function showDashboardFlow() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
    window.dashboardManager.showLoading();

    await window.archiveManager.loadArchiveIndex();
    window.archiveManager.populateDropdownSelector();

    window.dashboardManager.populateEnvDropdown();

    await loadDashboardData('current');
    
    // Render timeline on initial load
    window.timelineManager.renderTimeline();
    
    startVersionPolling();
    startMailboxPolling();
}

async function handleArchiveChange(event) {
    const archiveId = event.target.value;
    await loadDashboardData(archiveId);
    
    if (window.pollingInterval && archiveId !== 'current') {
        clearInterval(window.pollingInterval);
        console.log('Stopped version polling (switched to archive view).');
    } else if (archiveId === 'current') {
        startVersionPolling(); 
    }
    
    if (archiveId !== 'current') {
        stopMailboxPolling();
    } else {
        startMailboxPolling();
    }

    window.timelineManager.renderTimeline(); 
}

function handleEnvChange() {
    window.dashboardManager.render(); 
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
