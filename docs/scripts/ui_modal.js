// docs/scripts/ui_modal.js
import { openReport } from './ui_report.js';

let currentSessions = [];

export function handleCellClick(project, suite, date) {
    const record = window.dashboardManager?.data?.data[project]?.[suite]?.[date];
    if (!record?.sessions) return;

    // Show modal only if multiple sessions exist
    if (record.sessions.length > 1) {
        showSessionModal(project, suite, date, record.sessions);
    } else if (record.sessions.length === 1 && window.archiveManager.currentArchive === 'current') {
        openReport(record.sessions[0]);
    }
}

export function showSessionModal(project, suite, date, sessions) {
    const modal = document.getElementById('session-modal');
    const sessionList = document.getElementById('session-list');
    const displayName = suite.replace("Test Suites/", "");

    modal.querySelector('h3').textContent = displayName;
    sessionList.innerHTML = '';
    currentSessions = sessions;

    sessions.forEach(session => {
        const div = document.createElement('div');
        div.className = 'session-item';
        const startTime = new Date(session.start);
        const time = startTime.toLocaleTimeString('en-GB', { hour12: false });
        const passed = session.passed || 0;
        const total = session.test_cases || 0;
        const failed = total - passed;
        const colorClass = session.color === 'yellow' ? 'green' : (session.color || 'red');
        const profile = session.profile || 'N/A';

        div.innerHTML = `
            <div>
                <div class="session-profile-label">Profile: ${profile}</div>
                <div class="session-time-large">${time}</div>
            </div>
            <span class="pass-fail ${colorClass}">${passed}/${failed}</span>
        `;

        if (window.archiveManager.currentArchive === 'current') {
            div.onclick = () => openReport(session);
        } else {
            div.style.opacity = '0.7';
            div.style.cursor = 'default';
        }

        sessionList.appendChild(div);
    });

    modal.style.display = 'block';
}

export function setupModalCloseHandlers() {
    const modal = document.getElementById('session-modal');
    const closeBtn = modal.querySelector('.close');

    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        currentSessions = [];
    });

    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
            currentSessions = [];
        }
    });
}
