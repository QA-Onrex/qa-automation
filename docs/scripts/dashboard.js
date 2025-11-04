// docs/scripts/dashboard.js
import { CONFIG } from './config.js';

export class DashboardManager {
    constructor() {
        this.data = null;
    }

    async loadData(url = CONFIG.DASHBOARD_DATA_URL) {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
        this.data = await res.json();
        return this.data;
    }

    render() {
        if (!this.data) return;
        const { data, dates, last_updated } = this.data;
        document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;
        this.renderTable(data, dates);
        this.showDashboard();
    }

    renderTable(data, dates) {
        const header = `<tr><th>Test Suite</th>${dates.map(d => `<th>${d.slice(5)}</th>`).join('')}</tr>`;
        document.getElementById('table-header').innerHTML = header;

        const body = [];
        const projects = Object.keys(data).sort();
        for (const project of projects) {
            body.push(`<tr><td class="project-header">${project}</td>${'<td class="project-separator"></td>'.repeat(dates.length)}</tr>`);
            for (const suite of Object.keys(data[project]).sort()) {
                body.push(`<tr><td class="suite-name">${suite.replace("Test Suites/", "")}</td>`);
                for (const date of dates) {
                    const rec = data[project][suite][date];
                    if (rec) {
                        const color = rec.latest.color || 'red';
                        const passed = rec.latest.passed || 0;
                        const total = rec.latest.test_cases || 0;
                        const failed = total - passed;
                        body.push(
                            `<td class="${color}" onclick="handleCellClick('${project}', '${suite}', '${date}')">${passed}/${failed}</td>`
                        );
                    } else body.push('<td class="empty">–</td>');
                }
                body.push('</tr>');
            }
        }
        document.getElementById('table-body').innerHTML = body.join('');
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
