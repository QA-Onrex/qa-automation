// docs/scripts/dashboard.js
import { showTooltip, hideTooltip } from './ui_tooltip.js';
import { showSessionModal } from './ui_modal.js';
import { openReport } from './decryptor.js';
import { CONFIG } from './config.js';

export class DashboardManager {
    constructor() {
        this.data = null;
    }

    async loadData(customUrl = null) {
        const url = customUrl || CONFIG.DASHBOARD_DATA_URL;
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        this.data = await response.json();
        return this.data;
    }

    populateEnvDropdown() {
        const dropdown = document.getElementById('env-dropdown');
        dropdown.innerHTML = '';

        const envOptions = [
            { value: 'All', label: 'All Environments' },
            { value: 'Development', label: 'Development' },
            { value: 'Acceptance', label: 'Acceptance' }
        ];

        for (const optData of envOptions) {
            const opt = document.createElement('option');
            opt.value = optData.value;
            opt.textContent = optData.label;
            dropdown.appendChild(opt);
        }
    }

    render() {
        if (!this.data) return;
        const selectedEnv = document.getElementById('env-dropdown')?.value || 'All';
        const { data, dates, last_updated } = this.data;

        if (last_updated)
            document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;

        this.renderTable(data, dates, selectedEnv);
        this.showDashboard();
    }

    renderTable(data, dates, selectedEnv) {
        const headerHTML = ['<tr><th>Test Suite</th>' + dates.map(d => `<th>${d.slice(5)}</th>`).join('') + '</tr>'];
        document.getElementById('table-header').innerHTML = headerHTML.join('');

        const bodyHTML = [];
        const projects = Object.keys(data).sort();

        for (const project of projects) {
            let projectHasVisibleSuites = false;
            const suites = Object.keys(data[project]).sort();

            const suiteRows = [];
            for (const suite of suites) {
                let suiteHasEnvMatch = false;
                const dateCells = [];

                for (const date of dates) {
                    const record = data[project][suite][date];
                    if (!record) {
                        dateCells.push('<td class="empty">–</td>');
                        continue;
                    }

                    const sessions = record.sessions.filter(s => {
                        if (selectedEnv === 'All') return true;
                        if (selectedEnv === 'Development') return s.environment?.includes('intdev');
                        if (selectedEnv === 'Acceptance') return s.environment?.includes('intacc');
                        return false;
                    });

                    if (sessions.length > 0) suiteHasEnvMatch = true;

                    if (sessions.length === 0) {
                        dateCells.push('<td class="empty">–</td>');
                        continue;
                    }

                    // Determine color logic
                    let color = 'green';
                    const latest = sessions[0];
                    const hasFail = sessions.some(s => s.failed > 0 || s.error > 0 || s.incomplete > 0);
                    const allGreen = sessions.every(s => s.failed === 0 && s.error === 0 && s.incomplete === 0);

                    if (sessions.length === 1) {
                        color = hasFail ? 'red' : 'green';
                    } else {
                        if (allGreen) color = 'green';
                        else if (latest.failed === 0 && latest.error === 0 && latest.incomplete === 0) color = 'yellow';
                        else color = 'red';
                    }

                    const passed = latest.passed || 0;
                    const total = latest.test_cases || 0;
                    const failed = total - passed;

                    dateCells.push(
                        `<td class="${color}" 
                            onmousemove="showTooltip(event, '${project}', '${suite}', '${date}', '${selectedEnv}')"
                            onmouseleave="hideTooltip()" 
                            onclick="handleCellClick('${project}', '${suite}', '${date}', '${selectedEnv}')">
                            ${passed}/${failed}</td>`
                    );
                }

                if (suiteHasEnvMatch) {
                    suiteRows.push(`<tr><td class="suite-name">${suite.replace('Test Suites/', '')}</td>${dateCells.join('')}</tr>`);
                    projectHasVisibleSuites = true;
                }
            }

            if (projectHasVisibleSuites) {
                bodyHTML.push(`<tr><td class="project-header">${project}</td><td class="project-separator"></td></tr>`);
                bodyHTML.push(...suiteRows);
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

// Global handler for modal or report opening
window.handleCellClick = function (project, suite, date, selectedEnv) {
    const record = window.dashboardManager.data.data[project]?.[suite]?.[date];
    if (!record || !record.sessions) return;

    const sessions = record.sessions.filter(s => {
        if (selectedEnv === 'All') return true;
        if (selectedEnv === 'Development') return s.environment?.includes('intdev');
        if (selectedEnv === 'Acceptance') return s.environment?.includes('intacc');
        return false;
    });

    if (sessions.length > 1) {
        showSessionModal(project, suite, date, sessions);
    } else if (sessions.length === 1 && window.archiveManager.currentArchive === 'current') {
        openReport(project, suite, date, sessions[0]);
    }
};
