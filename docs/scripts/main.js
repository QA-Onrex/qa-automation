// docs/scripts/main.js

import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { setupModalCloseHandlers } from './ui_modal.js';
import { CONFIG } from './config.js';

let currentDashboardVersion = null; // Stores the last known version (timestamp)
const POLLING_INTERVAL_MS = 30000; 

// --- TIMELINE CONSTANTS ---
const MAX_CHART_HEIGHT_PX = 100; 
const MAX_SESSIONS_PER_HOUR = 20; 
const TIME_WINDOW_HOURS = 5 * 24; // 120 hours

/**
 * Renders the hourly timeline chart based on the selected environment filter.
 */
async function renderTimeline() {
    const timelineContainer = document.getElementById('timeline-chart');
    if (!timelineContainer) return;
    
    // Clear previous chart content
    timelineContainer.innerHTML = ''; 

    // 1. Determine the selected environment filter
    const envFilterElement = document.getElementById('env-dropdown'); 
    const selectedEnv = envFilterElement ? envFilterElement.value : 'all';
    const filterKey = selectedEnv === 'all' ? 'ALL' : selectedEnv;

    // 2. Fetch and filter data
    let data;
    try {
        const response = await fetch(CONFIG.TIMELINE_DATA_URL);
        if (!response.ok) throw new Error('Timeline data not found');
        data = await response.json();
    } catch (error) {
        console.error('Failed to load timeline data:', error);
        timelineContainer.innerHTML = '<p style="color: #c62828;">Failed to load timeline data. (Check: docs/timeline_data.json)</p>';
        return;
    }

    // --- FIX: Correct Environment Filtering Logic ---
    // The Python script uses the full URL for specific environments.
    const hourlyDataMap = data
        .filter(item => {
            if (filterKey === 'ALL') {
                return item.environment === 'ALL';
            }
            // For specific environments ('intdev', 'intacc'), check if the full URL contains the key.
            // Note: .toLowerCase() handles potential case issues in environment URLs.
            return item.environment.toLowerCase().includes(filterKey);
        })
        .reduce((acc, item) => {
            acc[item.hour] = item; 
            return acc;
        }, {});
    // --- END FIX ---
    
    // 3. Generate the timeline structure (Reversed Sorting)
    const now = new Date();
    
    // Calculate the start time (oldest hour block)
    const startDateTime = new Date();
    startDateTime.setHours(startDateTime.getHours() - TIME_WINDOW_HOURS);
    startDateTime.setMinutes(0, 0, 0);

    const columnsToRender = [];
    let lastRenderedDate = null; 

    // Iterate BACKWARDS from the current hour (i=0) to the oldest hour (i=TIME_WINDOW_HOURS)
    for (let i = 0; i <= TIME_WINDOW_HOURS; i++) {
        // Calculate the current hour block being rendered (newest first)
        const currentHour = new Date(now.getTime() - i * 60 * 60 * 1000);

        // Skip records older than the start of the 5-day window
        if (currentHour < startDateTime) continue;
        
        // Create the UTC hour key to match the Python script's output (e.g., 2025-11-06T18:00:00Z)
        const year = currentHour.getUTCFullYear();
        const month = String(currentHour.getUTCMonth() + 1).padStart(2, '0');
        const day = String(currentHour.getUTCDate()).padStart(2, '0');
        const hour = String(currentHour.getUTCHours()).padStart(2, '0');
        const hourKey = `${year}-${month}-${day}T${hour}:00:00Z`;

        const hourData = hourlyDataMap[hourKey];

        // 4. Calculate heights and create column HTML
        let columnHtml = '';
        
        if (hourData && hourData.total > 0) {
            const { passed, failed, total } = hourData;
            const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
            
            const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
            const totalHeightPx = total_capped * sessionHeightUnit; 
            
            const passedProportion = passed / total;
            const failedProportion = failed / total;

            const passedHeightPx = totalHeightPx * passedProportion;
            const failedHeightPx = totalHeightPx * failedProportion;
            
            // Time Label (HH:00) - Using 24H format
            const hourLabel = String(currentHour.getHours()).padStart(2, '0') + ':00';
            
            // Date Grouping Logic
            const dateString = `${String(currentHour.getDate()).padStart(2, '0')}.${String(currentHour.getMonth() + 1).padStart(2, '0')}`;
            let dateLabelHtml = '';
            
            // Since we are iterating backwards, we check if the PREVIOUS hour (i-1) was a different day.
            const previousHour = new Date(now.getTime() - (i - 1) * 60 * 60 * 1000);
            const prevDateString = `${String(previousHour.getDate()).padStart(2, '0')}.${String(previousHour.getMonth() + 1).padStart(2, '0')}`;
            
            // Only show the date on the first hour of a new day (when iterating backwards) or the very first column.
            if (i === 0 || dateString !== prevDateString) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
            }

            const labelTopPos = MAX_CHART_HEIGHT_PX - totalHeightPx + 5;

            // Bar rendering
            columnHtml = `
                <div class="bar-label" style="top: ${labelTopPos}px;">
                    <span class="pass-count">${passed}</span>/<span class="fail-count">${failed}</span>
                </div>
                <div class="stacked-bar-wrapper" style="height: ${totalHeightPx}px;">
                    <div class="bar-pass" style="height: ${passedHeightPx}px; bottom: ${failedHeightPx}px;"></div>
                    <div class="bar-fail" style="height: ${failedHeightPx}px; bottom: 0;"></div>
                </div>
                <div class="timeline-hour-label">${hourLabel}</div>
                ${dateLabelHtml}
            `;
        } else {
            // Render an empty bar for hours with no data
            const hourLabel = String(currentHour.getHours()).padStart(2, '0') + ':00';
            
            const dateString = `${String(currentHour.getDate()).padStart(2, '0')}.${String(currentHour.getMonth() + 1).padStart(2, '0')}`;
            let dateLabelHtml = '';
            
            const previousHour = new Date(now.getTime() - (i - 1) * 60 * 60 * 1000);
            const prevDateString = `${String(previousHour.getDate()).padStart(2, '0')}.${String(previousHour.getMonth() + 1).padStart(2, '0')}`;

            if (i === 0 || dateString !== prevDateString) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
            }
            
            columnHtml = `
                <div class="bar-label" style="top: 5px; color: #666;">
                    0/0
                </div>
                <div class="stacked-bar-wrapper" style="height: ${MAX_CHART_HEIGHT_PX}px;"></div>
                <div class="timeline-hour-label">${hourLabel}</div>
                ${dateLabelHtml}
            `;
        }
        
        // Add the column to the start of the array to achieve reverse sorting (newest on left)
        columnsToRender.unshift(`<div class="timeline-bar-column">${columnHtml}</div>`);
    }

    // 5. Inject all columns into the container
    timelineContainer.innerHTML = columnsToRender.join('');

    // Remove the scroll logic since reverse sorting removes the need to scroll to the end
}

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
    
    // CRITICAL: Call renderTimeline when environment changes
    document.getElementById('env-dropdown').addEventListener('change', () => {
        // First, handle table re-render
        handleEnvChange(); 
        // Then, update the timeline chart
        renderTimeline(); 
    });

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
            renderTimeline(); // NEW: Re-render timeline on data refresh
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
    
    // NEW: Render timeline after initial data load
    renderTimeline();
    
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
    
    // Also update the timeline when archive changes (since data is fetched from the archive)
    renderTimeline(); 
}

async function handleEnvChange() {
    window.dashboardManager.render(); // Re-render table with new filter
    // renderTimeline is called by the env-dropdown event listener in DOMContentLoaded
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
