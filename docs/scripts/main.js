// docs/scripts/main.js

import { AuthManager } from './auth.js';
import { DashboardManager } from './dashboard.js';
import { ArchiveManager } from './archive.js';
import { setupModalCloseHandlers } from './ui_modal.js';
import { CONFIG } from './config.js';

let currentDashboardVersion = null; 
const POLLING_INTERVAL_MS = 30000; 

// --- TIMELINE CONSTANTS ---
const MAX_CHART_HEIGHT_PX = 100; 
const MAX_SESSIONS_PER_HOUR = 20; 
const TIME_WINDOW_HOURS = 5 * 24; // 120 hours

/**
 * Renders the hourly timeline chart
 */
async function renderTimeline() {
    const timelineContainer = document.getElementById('timeline-chart');
    if (!timelineContainer) return;
    
    timelineContainer.innerHTML = ''; 

    // 1. Fetch timeline data
    let data;
    try {
        const response = await fetch(CONFIG.TIMELINE_DATA_URL);
        if (!response.ok) throw new Error('Timeline data not found');
        data = await response.json();
        console.log('Timeline data loaded:', data); // Debug log
    } catch (error) {
        console.error('Failed to load timeline data:', error);
        timelineContainer.innerHTML = '<p style="color: #c62828;">Failed to load timeline data.</p>';
        return;
    }

    // 2. Generate the timeline structure
    const columnsToRender = [];
    const now = new Date();
    
    // Calculate current UTC hour in milliseconds
    const currentUTCHourMs = Date.UTC(
        now.getUTCFullYear(),
        now.getUTCMonth(), 
        now.getUTCDate(),
        now.getUTCHours()
    );
    
    // Generate 120 hours (5 days) of timeline
    for (let i = 0; i <= TIME_WINDOW_HOURS; i++) {
        // Calculate hour block (going backwards from current hour)
        const hourBlockUTCMs = currentUTCHourMs - i * 60 * 60 * 1000;
        
        // Create UTC date for data lookup
        const hourBlockUTC = new Date(hourBlockUTCMs);
        
        // Generate the exact hour key that matches our data structure
        const year = hourBlockUTC.getUTCFullYear();
        const month = String(hourBlockUTC.getUTCMonth() + 1).padStart(2, '0');
        const day = String(hourBlockUTC.getUTCDate()).padStart(2, '0');
        const hour = String(hourBlockUTC.getUTCHours()).padStart(2, '0');
        const hourKey = `${year}-${month}-${day}T${hour}:00:00Z`;

        // Convert to local time for display
        const hourBlockLocal = new Date(hourBlockUTCMs);
        
        // Get data for this hour
        const hourData = data[hourKey];
        console.log(`Checking hour ${hourKey}:`, hourData); // Debug log

        // 3. Create column HTML
        let columnHtml = '';
        
        if (hourData && hourData.total > 0) {
            const { passed, failed, total } = hourData;
            const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
            
            const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
            const totalHeightPx = total_capped * sessionHeightUnit;
            
            // Calculate heights for stacked bars
            const passedHeightPx = totalHeightPx * (passed / total);
            const failedHeightPx = totalHeightPx * (failed / total);
            
            // Time label (local time)
            const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
            
            // Date label
            const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
            const dateLabelHtml = i === 0 ? `<div class="timeline-date-label">${dateString}</div>` : '';
            
            // Position label above the bar
            const labelTopPos = MAX_CHART_HEIGHT_PX - totalHeightPx - 15;

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
            
            console.log(`Rendering bar for ${hourKey}: ${passed}/${failed}`); // Debug log
        } else {
            // Empty bar for hours with no data
            const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
            const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
            const dateLabelHtml = i === 0 ? `<div class="timeline-date-label">${dateString}</div>` : '';
            
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

    // 4. Inject columns (newest on left)
    timelineContainer.innerHTML = columnsToRender.join('');
    console.log('Timeline rendered with', columnsToRender.length, 'columns'); // Debug log
}


window.addEventListener('DOMContentLoaded', async () => {
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();
    window.archiveManager = new ArchiveManager();

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
    
    // CRITICAL: Call renderTimeline when environment changes
    document.getElementById('env-dropdown').addEventListener('change', () => {
        handleEnvChange(); 
        renderTimeline(); 
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
            renderTimeline(); 
        } else if (!currentDashboardVersion) {
            currentDashboardVersion = versionData.version;
        }
    } catch (error) {
        console.error('Version check failed:', error);
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
    
    // RENDER TIMELINE ON INITIAL LOAD
    renderTimeline();
    
    startVersionPolling(); 
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
    
    renderTimeline(); 
}

function handleEnvChange() {
    window.dashboardManager.render(); 
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
