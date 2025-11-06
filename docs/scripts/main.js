// docs/scripts/main.js

import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { setupModalCloseHandlers } from './ui_modal.js';
import { CONFIG } from './config.js';

let currentDashboardVersion = null; // Stores the last known version (timestamp)
const POLLING_INTERVAL_MS = 30000; // Check every 30 seconds (adjust as needed)

// --- TIMELINE CONSTANTS ---
const MAX_CHART_HEIGHT_PX = 100; 
const MAX_SESSIONS_PER_HOUR = 20; 

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

    // Filter the data based on the environment key
    const filteredData = data.filter(item => {
        return item.environment === filterKey;
    });

    // Group the data by hour for easy lookup (key: hour_iso_string)
    const hourlyDataMap = filteredData.reduce((acc, item) => {
        acc[item.hour] = item; 
        return acc;
    }, {});
    
    // 3. Generate the last 5 days (120 hours) timeline structure
    const now = new Date();
    const numHours = 5 * 24; // 5 days * 24 hours
    
    // Calculate the start time (5 days ago, rounded to the nearest hour start)
    const startDateTime = new Date();
    startDateTime.setHours(startDateTime.getHours() - numHours);
    startDateTime.setMinutes(0, 0, 0);

    const columnsToRender = [];
    let lastRenderedDate = null; // Used for grouping the date labels

    // Iterate from the start hour up to the current hour (inclusive)
    for (let i = 0; i <= numHours; i++) {
        const currentHour = new Date(startDateTime.getTime() + i * 60 * 60 * 1000);
        
        // Skip future hours
        if (currentHour > now) continue;

        // Create the UTC hour key to match the Python script's output
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
            
            // Re-calculate total_capped based on current total, just in case data is stale
            const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
            
            const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
            
            // BUG FIX: This is the actual height the bar must occupy (0 to 100px)
            const totalHeightPx = total_capped * sessionHeightUnit; 
            
            // Calculate pixel heights for pass/fail bars
            const passedProportion = passed / total;
            const failedProportion = failed / total;

            const passedHeightPx = totalHeightPx * passedProportion;
            const failedHeightPx = totalHeightPx * failedProportion;
            
            // Time Label (HH:00)
            const hourLabel = currentHour.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }).substring(0, 2) + ':00';
            
            // --- NEW DATE GROUPING LOGIC ---
            const dateString = `${String(currentHour.getDate()).padStart(2, '0')}.${String(currentHour.getMonth() + 1).padStart(2, '0')}`;
            let dateLabelHtml = '';
            
            // Show the date label only on the first hour of a new day
            if (dateString !== lastRenderedDate) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                lastRenderedDate = dateString;
            } else {
                // If it's not a new day, only render the hour label
                lastRenderedDate = dateString;
            }
            
            // The bar-label positioning is now calculated relative to the top of the column
            const labelTopPos = MAX_CHART_HEIGHT_PX - totalHeightPx + 5;

            // Bar rendering: stacked-bar-wrapper height is set to the dynamic totalHeightPx
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
            const hourLabel = currentHour.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }).substring(0, 2) + ':00';
            const dateString = `${String(currentHour.getDate()).padStart(2, '0')}.${String(currentHour.getMonth() + 1).padStart(2, '0')}`;
            
            let dateLabelHtml = '';
            if (dateString !== lastRenderedDate) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                lastRenderedDate = dateString;
            } else {
                lastRenderedDate = dateString;
            }
            
            // The empty bar case still needs to show the labels and the horizontal baseline
            columnHtml = `
                <div class="bar-label" style="top: 5px; color: #666;">
                    0/0
                </div>
                <div class="stacked-bar-wrapper" style="height: ${MAX_CHART_HEIGHT_PX}px;"></div>
                <div class="timeline-hour-label">${hourLabel}</div>
                ${dateLabelHtml}
            `;
        }

        columnsToRender.push(`<div class="timeline-bar-column">${columnHtml}</div>`);
    }

    // 5. Inject all columns into the container
    timelineContainer.innerHTML = columnsToRender.join('');

    // Scroll to the newest data (the far right) on load
    timelineContainer.scrollLeft = timelineContainer.scrollWidth;
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
