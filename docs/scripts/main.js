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
 * Renders the hourly timeline chart based on the selected environment filter.
 */
async function renderTimeline() {
    const timelineContainer = document.getElementById('timeline-chart');
    if (!timelineContainer) return;
    
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

    // Correct Environment Filtering Logic
    const hourlyDataMap = data
        .filter(item => {
            if (filterKey === 'ALL') {
                return item.environment === 'ALL';
            }
            // Check if the full environment URL contains the selected filter key (e.g., 'intacc' or 'intdev').
            return item.environment.toLowerCase().includes(filterKey);
        })
        .reduce((acc, item) => {
            // Group data by its UTC hour key
            acc[item.hour] = item; 
            return acc;
        }, {});
    
    // 3. Generate the timeline structure (REVERSED SORTING: Newest on Left)
    const columnsToRender = [];

    // Find the current date/time and round down to the start of the current *UTC* hour.
    const nowUTC = new Date();
    // Use UTC methods to ensure the baseline time is aligned with the UTC data keys.
    nowUTC.setUTCMinutes(0, 0, 0); 
    
    // Iterate backward from the most recent hour (i=0) to the oldest hour (i=TIME_WINDOW_HOURS)
    for (let i = 0; i <= TIME_WINDOW_HOURS; i++) {
        
        // Calculate the hour by subtracting from the fixed 'nowUTC' time.
        const currentHour = new Date(nowUTC.getTime() - i * 60 * 60 * 1000);
        
        // CRITICAL FIX: Generate the UTC hour key using explicit UTC getters
        // This guarantees the key exactly matches the data format: YYYY-MM-DDTHH:00:00Z
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
            
            // Time Label (HH:00) - Use local time for display
            const hourLabel = String(currentHour.getHours()).padStart(2, '0') + ':00';
            
            // Date Grouping Logic
            const dateString = `${String(currentHour.getDate()).padStart(2, '0')}.${String(currentHour.getMonth() + 1).padStart(2, '0')}`;
            let dateLabelHtml = '';
            
            // Show the date if it's the newest column (i=0) or if the next hour block has a different day.
            if (i === 0) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
            } else {
                // Calculate the time for the *next* hour block in the sequence (i-1)
                const nextHour = new Date(nowUTC.getTime() - (i - 1) * 60 * 60 * 1000);
                const nextDateString = `${String(nextHour.getDate()).padStart(2, '0')}.${String(nextHour.getMonth() + 1).padStart(2, '0')}`;

                if (dateString !== nextDateString) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                }
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
            
            if (i === 0) {
                dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
            } else {
                const nextHour = new Date(nowUTC.getTime() - (i - 1) * 60 * 60 * 1000);
                const nextDateString = `${String(nextHour.getDate()).padStart(2, '0')}.${String(nextHour.getMonth() + 1).padStart(2, '0')}`;

                if (dateString !== nextDateString) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                }
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
        
        // Append the column to maintain newest-on-left order.
        columnsToRender.push(`<div class="timeline-bar-column">${columnHtml}</div>`);
    }

    // 5. Inject all columns into the container
    timelineContainer.innerHTML = columnsToRender.join('');
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
