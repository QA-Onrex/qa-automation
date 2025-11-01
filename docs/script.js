// Password hash - this should be set during deployment/build process
const PASSWORD_HASH = '3718db2207be42cabda43cdfedb181ffef206cfda7ad775c7ba9e524104d2a32';

let dashboardData = null;
let currentSessions = [];

// Authentication Functions
async function hashPassword(password) {
    const msgBuffer = new TextEncoder().encode(password);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

async function checkPassword() {
    const password = document.getElementById('password-input').value;
    const hash = await hashPassword(password);
    
    if (hash === PASSWORD_HASH) {
        sessionStorage.setItem('reportPassword', password);
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        loadDashboardData();
    } else {
        document.getElementById('error-message').style.display = 'block';
    }
}

// Dashboard Data Functions
async function loadDashboardData() {
    try {
        const response = await fetch('dashboard_data.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        dashboardData = await response.json();
        renderDashboard();
    } catch (error) {
        console.error('Failed to load dashboard data:', error);
        document.getElementById('loading-message').innerHTML = 
            'Error loading dashboard data. Please try refreshing the page.';
    }
}

function renderDashboard() {
    if (!dashboardData) return;

    const { data, dates, last_updated } = dashboardData;
    
    // Update last updated timestamp
    if (last_updated) {
        document.getElementById('last-updated').textContent = 
            `Last updated: ${last_updated}`;
    }

    // Build table header
    const headerHTML = ['<tr><th>Test Suite</th>' + dates.map(d => `<th>${d.slice(5)}</th>`).join('') + '</tr>'];
    document.getElementById('table-header').innerHTML = headerHTML.join('');

    // Build table body
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
    document.getElementById('loading-message').style.display = 'none';
    document.getElementById('table-container').style.display = 'block';
}

// Tooltip Functions
function showTooltip(e, project, suite, date) {
    if (!dashboardData) return;
    const record = dashboardData.data[project]?.[suite]?.[date];
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
    
    // Get tooltip dimensions
    const tooltipHeight = tooltip.offsetHeight;
    const tooltipWidth = tooltip.offsetWidth;
    
    // Get viewport dimensions
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    
    // Default position (below and to the right of cursor)
    let top = e.pageY + 10;
    let left = e.pageX + 10;
    
    // Check if tooltip would go off bottom of screen
    if (top + tooltipHeight > viewportHeight) {
        top = e.pageY - tooltipHeight - 10; // Position above cursor
    }
    
    // Check if tooltip would go off right of screen
    if (left + tooltipWidth > viewportWidth) {
        left = e.pageX - tooltipWidth - 10; // Position to the left of cursor
    }
    
    // Ensure tooltip doesn't go off top of screen
    if (top < 0) {
        top = 10;
    }
    
    // Ensure tooltip doesn't go off left of screen
    if (left < 0) {
        left = 10;
    }
    
    tooltip.style.top = top + 'px';
    tooltip.style.left = left + 'px';
}

function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}

// Session Modal Functions
function showSessionModal(project, suite, date) {
    const record = dashboardData.data[project]?.[suite]?.[date];
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

// Report Decryption Functions
async function decryptBytesAES(encryptedBytes, password) {
    if (encryptedBytes.length < 28) {
        throw new Error('Invalid encrypted data length. Data is too short.');
    }
    const salt = encryptedBytes.slice(0, 16);
    const nonce = encryptedBytes.slice(16, 28);
    const ciphertext = encryptedBytes.slice(28);
    
    console.log('[DECRYPTOR:PARAMS] Salt (First 10 bytes HEX):', Array.from(salt.slice(0, 10)).map(b => b.toString(16).padStart(2, '0')).join(''));
    console.log('[DECRYPTOR:PARAMS] Nonce (HEX):', Array.from(nonce).map(b => b.toString(16).padStart(2, '0')).join(''));

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
    const record = dashboardData.data[project]?.[suite]?.[date];
    if (!record) return;
    
    // Use specific session if provided, otherwise use latest
    const session = specificSession || record.latest;
    if (!session || !session.html_file) return;
    
    const password = sessionStorage.getItem('reportPassword');
    if (!password) return alert('Password missing!');

    try {
        // Fetch the encrypted file (STANDARD Base64 encoded)
        const resp = await fetch(session.html_file);
        if (!resp.ok) throw new Error(`HTTP error! status: ${resp.status}`);
        const base64Data = await resp.text();
        
        console.log('[FETCH:OUTPUT] Base64 Data Length:', base64Data.length);
        console.log('[FETCH:OUTPUT] Base64 Data Start:', base64Data.substring(0, 50));
        
        // Decode STANDARD base64 to get raw binary string
        const binaryString = atob(base64Data);
        
        // Convert binary string to encrypted bytes (Uint8Array)
        const encryptedBytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
            encryptedBytes[i] = binaryString.charCodeAt(i);
        }
        
        // Decrypt the bytes
        const decryptedBytes = await decryptBytesAES(encryptedBytes, password);
        
        // Create and open the HTML report
        const decryptedText = new TextDecoder().decode(decryptedBytes);
        const blob = new Blob([decryptedText], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank');
    } catch (e) {
        console.error('Failed to decrypt report:', e);
        
        let msg = 'Failed to decrypt report. The password may be incorrect or the data is corrupt.';
        if (e.name === 'OperationError') {
            msg = 'Decryption failed: Check your password or the report data is tampered.';
        }
        alert(msg + ' Check the browser console for details (F12).');
    }
}

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    // Set up event listeners
    document.getElementById('login-button').addEventListener('click', checkPassword);
    document.getElementById('password-input').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') checkPassword();
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

    // Check for saved password
    const savedPassword = sessionStorage.getItem('reportPassword');
    
    if (PASSWORD_HASH && savedPassword) {
        hashPassword(savedPassword).then(hash => {
            if (hash === PASSWORD_HASH) {
                document.getElementById('login-container').style.display = 'none';
                document.getElementById('dashboard-content').style.display = 'block';
                loadDashboardData();
            } else {
                sessionStorage.removeItem('reportPassword');
            }
        });
    } else if (!PASSWORD_HASH) {
        document.getElementById('login-container').style.display = 'none';
        document.getElementById('dashboard-content').style.display = 'block';
        loadDashboardData();
    }
});
