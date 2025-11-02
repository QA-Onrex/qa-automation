// Configuration constants
const CONFIG = {
    PASSWORD_HASH: '3718db2207be42cabda43cdfedb181ffef206cfda7ad775c7ba9e524104d2a32',
    DASHBOARD_DATA_URL: 'dashboard_data.json',
    ARCHIVE_INDEX_URL: 'archive/archive_index.json',
    ARCHIVE_BASE_URL: 'archive/',
    MAX_TOOLTIP_OFFSET: 10,
    TOOLTIP_PADDING: 10
    AUTO_REFRESH_INTERVAL: 30000 // 30 seconds
};

// Auth Manager
class AuthManager {
    async hashPassword(password) {
        const msgBuffer = new TextEncoder().encode(password);
        const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }

    async authenticate(password) {
        const hash = await this.hashPassword(password);
        return hash === CONFIG.PASSWORD_HASH;
    }

    hasValidSession() {
        const savedPassword = sessionStorage.getItem('reportPassword');
        return !!savedPassword;
    }
}

// Archive Manager
class ArchiveManager {
    constructor() {
        this.archives = [];
        this.currentArchive = 'current';
    }

    async loadArchiveIndex() {
        try {
            const response = await fetch(CONFIG.ARCHIVE_INDEX_URL);
            if (!response.ok) throw new Error('Failed to load archive index');
            this.archives = await response.json();
            return this.archives;
        } catch (error) {
            console.error('Error loading archive index:', error);
            this.archives = [];
            return [];
        }
    }

    formatArchiveDisplayName(archiveId) {
        if (archiveId === 'current') return 'Current (Live)';
        
        const [year, month] = archiveId.split('_');
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    }

    getArchiveFileName(archiveId) {
        if (archiveId === 'current') return CONFIG.DASHBOARD_DATA_URL;
        return `${CONFIG.ARCHIVE_BASE_URL}${archiveId}_dashboard_data.json`;
    }
}

// Dashboard Manager
class DashboardManager {
    constructor() {
        this.data = null;
        this.lastUpdate = null;
        this.refreshInterval = null;
    }

    async loadData(customUrl = null) {
        try {
            const url = customUrl || CONFIG.DASHBOARD_DATA_URL;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            this.data = await response.json();
            return this.data;
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            throw error;
        }
    }

    render() {
        if (!this.data) return;

        const { data, dates, last_updated } = this.data;
        
        // Update last updated timestamp
        if (last_updated) {
            document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;
        }

        this.renderTable(data, dates);
        this.showDashboard();
    }

    renderTable(data, dates) {
        const headerHTML = ['<tr><th>Test Suite</th>' + dates.map(d => `<th>${d.slice(5)}</th>`).join('') + '</tr>'];
        document.getElementById('table-header').innerHTML = headerHTML.join('');

        const bodyHTML = [];
        const projects = Object.keys(data).sort();

        for (const project of projects) {
            bodyHTML.push(`<tr><td class="project-header">${project}</td>` + 
                '<td class="project-separator"></td>'.repeat(dates.length) + '</tr>');
            
            const suites = Object.keys(data[project]).sort();
            for (const suite of suites) {
                const displayName = suite.replace("Test Suites/", "");
                bodyHTML.push(`<tr><td class="suite-name">${displayName}</td>`);
                
                for (const date of dates) {
                    if (date in data[project][suite]) {
                        const record = data[project][suite][date];
                        const color = record.latest.color;
                        const passed = record.latest.passed || 0;
                        const total = record.latest.test_cases || 0;
                        const failed = total - passed;
                        
                        bodyHTML.push(
                            `<td class="${color}" ` +
                            `onmousemove="showTooltip(event, '${project}', '${suite}', '${date}')" ` +
                            `onmouseleave="hideTooltip()" ` +
                            `onclick="handleCellClick('${project}', '${suite}', '${date}')">` +
                            `${passed}/${failed}</td>`
                        );
                    } else {
                        bodyHTML.push('<td class="empty">–</td>');
                    }
                }
                bodyHTML.push('</tr>');
            }
        }

        document.getElementById('table-body').innerHTML = bodyHTML.join('');
    }

    showDashboard() {
        document.getElementById('loading-message').style.display = 'none';
        document.getElementById('table-container').style.display = 'block';
    }

    showLoading() {
        document.getElementById('loading-message').style.display = 'block';
        document.getElementById('table-container').style.display = 'none';
    }
    
    startAutoRefresh() {
        if (!CONFIG.AUTO_REFRESH_INTERVAL) return;
        
        this.stopAutoRefresh();
        
        this.refreshInterval = setInterval(async () => {
            await this.checkForUpdates();
        }, CONFIG.AUTO_REFRESH_INTERVAL);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async checkForUpdates() {
        // Only check current data, not archives
        if (window.archiveManager.currentArchive !== 'current') return;

        try {
            const response = await fetch(CONFIG.DASHBOARD_DATA_URL + '?t=' + Date.now());
            if (!response.ok) return;
            
            const newData = await response.json();
            
            // If last_updated changed, refresh
            if (this.lastUpdate && newData.last_updated !== this.lastUpdate) {
                await this.loadData();
                this.render();
            }
            
            this.lastUpdate = newData.last_updated;
            
        } catch (error) {
            console.log('Auto-refresh check failed:', error);
        }
    }

    // Update loadData to store last_update
    async loadData(customUrl = null) {
        try {
            const url = customUrl || CONFIG.DASHBOARD_DATA_URL;
            const response = await fetch(url);
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            this.data = await response.json();
            this.lastUpdate = this.data.last_updated;
            return this.data;
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            throw error;
        }
    }
}

// Tooltip functions
function showTooltip(e, project, suite, date) {
    if (!window.dashboardManager?.data) return;
    
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record) return;
    
    const tooltip = document.getElementById('tooltip');
    const start = new Date(record.latest.start);
    const end = new Date(record.latest.end);
    const formatDate = (d) => d.getFullYear().toString().slice(2) + '/' + 
        String(d.getMonth()+1).padStart(2,'0') + '/' + String(d.getDate()).padStart(2,'0') + ' - ' +
        String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');
    
    const totalSeconds = Math.floor(record.latest.duration * 60);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    const durationStr = String(minutes).padStart(2,'0') + ':' + String(seconds).padStart(2,'0');
    
    tooltip.innerHTML = `
        <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${record.latest.profile || 'N/A'}</strong></div>
        <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${record.latest.test_cases || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${record.latest.passed || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${record.latest.failed || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${record.latest.error || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Incomplete:</span>${record.latest.incomplete || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${record.latest.skipped || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Retry:</span>${record.latest.retry_count || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${formatDate(start)}</div>
        <div class='tooltip-row'><span class='tooltip-label'>End:</span>${formatDate(end)}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
    `;
    
    tooltip.style.display = 'block';
    
    // Position tooltip
    const tooltipHeight = tooltip.offsetHeight;
    const tooltipWidth = tooltip.offsetWidth;
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    let top = e.pageY + CONFIG.TOOLTIP_PADDING;
    let left = e.pageX + CONFIG.TOOLTIP_PADDING;

    if (top + tooltipHeight > viewportHeight) {
        top = e.pageY - tooltipHeight - CONFIG.TOOLTIP_PADDING;
    }

    if (left + tooltipWidth > viewportWidth) {
        left = e.pageX - tooltipWidth - CONFIG.TOOLTIP_PADDING;
    }

    top = Math.max(CONFIG.TOOLTIP_PADDING, top);
    left = Math.max(CONFIG.TOOLTIP_PADDING, left);

    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
}

function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}

// Cell click handler
function handleCellClick(project, suite, date) {
    if (!window.dashboardManager?.data) return;
    
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record || !record.sessions) return;
    
    // Only show modal for multiple sessions
    if (record.sessions.length > 1) {
        showSessionModal(project, suite, date);
    }
    // For single sessions in current data, open report directly
    else if (record.sessions.length === 1 && window.archiveManager.currentArchive === 'current') {
        openReport(project, suite, date, record.sessions[0]);
    }
    // For single sessions in archive data, do nothing
    else {
        // No action for single sessions in archives
    }
}

// Modal functions
let currentSessions = [];

function showSessionModal(project, suite, date) {
    if (!window.dashboardManager?.data) return;
    
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record || !record.sessions) return;
    
    currentSessions = record.sessions;
    const modal = document.getElementById('session-modal');
    const sessionList = document.getElementById('session-list');
    
    // Get the display name for the test suite
    const displayName = suite.replace("Test Suites/", "");
    
    // Update modal title with test suite name
    const modalTitle = modal.querySelector('h3');
    modalTitle.textContent = displayName;
    
    sessionList.innerHTML = '';
    
    currentSessions.forEach((session, index) => {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        
        // Only make clickable for current data
        if (window.archiveManager.currentArchive === 'current') {
            sessionItem.onclick = () => openReport(project, suite, date, session);
            sessionItem.style.cursor = 'pointer';
        } else {
            sessionItem.style.cursor = 'default';
            sessionItem.style.opacity = '0.8';
        }
        
        const startTime = new Date(session.start);
        const timeString = startTime.toLocaleTimeString('en-GB', { 
            hour: '2-digit', 
            minute: '2-digit', 
            second: '2-digit',
            hour12: false 
        });
        const passed = session.passed || 0;
        const total = session.test_cases || 0;
        const failed = total - passed;
        
        // Determine color class based on session color
        let colorClass = session.color.toLowerCase();
        if (colorClass === 'yellow') {
            colorClass = 'green';
        }
        
        // Get the profile name, defaulting to 'N/A' if missing
        const profileName = session.profile || 'N/A';
        
        // Display the Profile name above the large time
        sessionItem.innerHTML = `
            <div>
                <div class="session-profile-label">Profile: ${profileName}</div>
                <div class="session-time-large">${timeString}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span class="pass-fail ${colorClass}">${passed}/${failed}</span>
            </div>
        `;
        
        sessionList.appendChild(sessionItem);
    });
    
    modal.style.display = 'block';
}

// Crypto functions
async function decryptBytesAES(encryptedBytes, password) {
    if (encryptedBytes.length < 28) {
        throw new Error('Invalid encrypted data length. Data is too short.');
    }
    
    const salt = encryptedBytes.slice(0, 16);
    const nonce = encryptedBytes.slice(16, 28);
    const ciphertext = encryptedBytes.slice(28);
    
    console.log('[DECRYPTOR:PARAMS] Salt (First 10 bytes HEX):', 
        Array.from(salt.slice(0, 10)).map(b => b.toString(16).padStart(2, '0')).join(''));
    console.log('[DECRYPTOR:PARAMS] Nonce (HEX):', 
        Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join(''));

    const enc = new TextEncoder();
    const keyMaterial = await crypto.subtle.importKey(
        'raw',
        enc.encode(password),
        { name: 'PBKDF2' },
        false,
        ['deriveKey']
    );

    const key = await crypto.subtle.deriveKey(
        { name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' },
        keyMaterial,
        { name: 'AES-GCM', length: 256 },
        false,
        ['decrypt']
    );

    const decrypted = await crypto.subtle.decrypt({
        name: 'AES-GCM',
        iv: nonce
    }, key, ciphertext);

    return new Uint8Array(decrypted);
}

async function openReport(project, suite, date, specificSession = null) {
    // Disable report opening for archives
    if (window.archiveManager.currentArchive !== 'current') {
        alert('Detailed reports are only available for current data. Please switch to "Current (Live)" view to access detailed reports.');
        return;
    }
    
    if (!window.dashboardManager?.data) return;
    
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record) return;
    
    const session = specificSession || record.latest;
    if (!session || !session.html_file) return;
    
    const password = sessionStorage.getItem('reportPassword');
    if (!password) {
        alert('Password missing!');
        return;
    }

    try {
        const resp = await fetch(session.html_file);
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const base64Data = await resp.text();
        
        console.log('[FETCH:OUTPUT] Base64 Data Length:', base64Data.length);
        
        const binaryString = atob(base64Data);
        const encryptedBytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            encryptedBytes[i] = binaryString.charCodeAt(i);
        }
        
        const decryptedBytes = await decryptBytesAES(encryptedBytes, password);
        const decryptedText = new TextDecoder().decode(decryptedBytes);
        const blob = new Blob([decryptedText], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
        
    } catch (error) {
        console.error('Failed to decrypt report:', error);
        let message = 'Failed to decrypt report. The password may be incorrect or the data is corrupt.';
        if (error.name === 'OperationError') {
            message = 'Decryption failed: Check your password or the report data is tampered.';
        }
        alert(message + ' Check the browser console for details (F12).');
    }
}

// Archive functions
async function initializeArchiveSelector() {
    await window.archiveManager.loadArchiveIndex();
    populateDropdownSelector();
}

function populateDropdownSelector() {
    const dropdown = document.getElementById('archive-dropdown');
    dropdown.innerHTML = '<option value="current">Current (Live)</option>';
    
    window.archiveManager.archives.forEach(archiveId => {
        const option = document.createElement('option');
        option.value = archiveId;
        option.textContent = window.archiveManager.formatArchiveDisplayName(archiveId);
        dropdown.appendChild(option);
    });
}

async function handleArchiveChange(event) {
    const archiveId = event.target.value;
    await selectArchive(archiveId);
}

async function selectArchive(archiveId) {
    window.archiveManager.currentArchive = archiveId;
    
    // Load and display archive data
    await loadArchiveData(archiveId);
}

async function loadArchiveData(archiveId) {
    try {
        window.dashboardManager.showLoading();
        
        const dataUrl = window.archiveManager.getArchiveFileName(archiveId);
        await window.dashboardManager.loadData(dataUrl);
        window.dashboardManager.render();
        
    } catch (error) {
        console.error(`Error loading archive ${archiveId}:`, error);
        document.getElementById('loading-message').innerHTML = 
            `Error loading archive data. Please try selecting a different archive.`;
        
        // Fall back to current data
        if (archiveId !== 'current') {
            setTimeout(() => selectArchive('current'), 2000);
        }
    }
}

// Main application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize managers
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();
    window.archiveManager = new ArchiveManager();

    // Set up event listeners
    document.getElementById('login-button').addEventListener('click', handleLogin);
    document.getElementById('password-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleLogin();
    });
    
    // Archive selector events
    document.getElementById('archive-dropdown').addEventListener('change', handleArchiveChange);
    
    // Environment filter event (placeholder for future implementation)
    document.getElementById('env-filter').addEventListener('change', function(e) {
        console.log('Environment filter changed to:', e.target.value);
        // Filtering logic will be implemented later
    });
    
    // Modal close handlers
    document.querySelector('.close').addEventListener('click', function() {
        document.getElementById('session-modal').style.display = 'none';
        currentSessions = [];
    });
    
    window.addEventListener('click', function(event) {
        if (event.target === document.getElementById('session-modal')) {
            document.getElementById('session-modal').style.display = 'none';
            currentSessions = [];
        }
    });

    // Check for existing session
    checkExistingSession();
});

async function handleLogin() {
    const password = document.getElementById('password-input').value;
    
    if (await window.authManager.authenticate(password)) {
        sessionStorage.setItem('reportPassword', password);
        showDashboard();
        await initializeArchiveSelector();
        await loadDashboardData();
    } else {
        document.getElementById('error-message').style.display = 'block';
    }
}

async function checkExistingSession() {
    if (window.authManager.hasValidSession()) {
        showDashboard();
        await initializeArchiveSelector();
        await loadDashboardData();
    } else if (!CONFIG.PASSWORD_HASH) {
        showDashboard();
        await initializeArchiveSelector();
        await loadDashboardData();
    }
}

async function loadDashboardData() {
    try {
        window.dashboardManager.showLoading();
        await window.dashboardManager.loadData();
        window.dashboardManager.render();
    } catch (error) {
        document.getElementById('loading-message').innerHTML = 
            'Error loading dashboard data. Please try refreshing the page.';
    }
}

function showDashboard() {
    document.getElementById('login-container').style.display = 'none';
    document.getElementById('dashboard-content').style.display = 'block';
}
