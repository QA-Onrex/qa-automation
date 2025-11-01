// Configuration constants
const CONFIG = {
    PASSWORD_HASH: '3718db2207be42cabda43cdfedb181ffef206cfda7ad775c7ba9e524104d2a32',
    DASHBOARD_DATA_URL: 'dashboard_data.json',
    MAX_TOOLTIP_OFFSET: 10,
    TOOLTIP_PADDING: 10
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
        return savedPassword && CONFIG.PASSWORD_HASH;
    }
}

// Dashboard Manager
class DashboardManager {
    constructor() {
        this.data = null;
    }

    async loadData() {
        try {
            const response = await fetch(CONFIG.DASHBOARD_DATA_URL);
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
                            `onclick="showSessionModal('${project}', '${suite}', '${date}')">` +
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

// Modal functions
let currentSessions = [];

function showSessionModal(project, suite, date) {
    if (!window.dashboardManager?.data) return;
    
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record || !record.sessions) return;
    
    // Single session - open directly
    if (record.sessions.length === 1) {
        openReport(project, suite, date, record.sessions[0]);
        return;
    }

    // Multiple sessions - show modal
    currentSessions = record.sessions;
    const modal = document.getElementById('session-modal');
    const sessionList = document.getElementById('session-list');
    
    sessionList.innerHTML = '';
    
    currentSessions.forEach((session, index) => {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        sessionItem.onclick = () => openReport(project, suite, date, session);
        
        const startTime = new Date(session.start);
        const timeString = startTime.toLocaleTimeString();
        const passed = session.passed || 0;
        const total = session.test_cases || 0;
        const failed = total - passed;
        const statusClass = `status-${session.color.toLowerCase()}`;
        
        sessionItem.innerHTML = `
            <div>
                <div>Session ${index + 1}</div>
                <div class="session-time">${timeString}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>${passed}/${failed}</span>
                <span class="session-status ${statusClass}">${session.color}</span>
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

// Main application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize managers
    window.authManager = new AuthManager();
    window.dashboardManager = new DashboardManager();

    // Set up event listeners
    document.getElementById('login-button').addEventListener('click', handleLogin);
    document.getElementById('password-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') handleLogin();
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
        await loadDashboardData();
    } else {
        document.getElementById('error-message').style.display = 'block';
    }
}

async function checkExistingSession() {
    if (window.authManager.hasValidSession()) {
        showDashboard();
        await loadDashboardData();
    } else if (!CONFIG.PASSWORD_HASH) {
        showDashboard();
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
