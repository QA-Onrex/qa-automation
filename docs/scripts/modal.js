class ModalManager {
    constructor() {
        this.modal = document.getElementById('session-modal');
        this.sessionList = document.getElementById('session-list');
        this.currentSessions = [];
        this.setupEventListeners();
    }

    setupEventListeners() {
        document.querySelector('.close').addEventListener('click', () => this.hide());
        window.addEventListener('click', (event) => {
            if (event.target === this.modal) {
                this.hide();
            }
        });
    }

    showSessions(project, suite, date) {
        if (!window.app?.dashboard?.data) return;
        
        const record = window.app.dashboard.data.data[project]?.[suite]?.[date];
        if (!record || !record.sessions) return;
        
        // Single session - open directly
        if (record.sessions.length === 1) {
            window.app.cryptoManager.openReport(project, suite, date, record.sessions[0]);
            return;
        }

        // Multiple sessions - show modal
        this.currentSessions = record.sessions;
        this.renderSessionList(project, suite, date);
        this.modal.style.display = 'block';
    }

    renderSessionList(project, suite, date) {
        this.sessionList.innerHTML = '';
        
        this.currentSessions.forEach((session, index) => {
            const sessionItem = document.createElement('div');
            sessionItem.className = 'session-item';
            sessionItem.onclick = () => window.app.cryptoManager.openReport(project, suite, date, session);
            
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
            
            this.sessionList.appendChild(sessionItem);
        });
    }

    hide() {
        this.modal.style.display = 'none';
        this.currentSessions = [];
    }
}
