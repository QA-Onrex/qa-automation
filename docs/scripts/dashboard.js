class Dashboard {
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
            document.getElementById('last-updated').textContent = 
                `Last updated: ${last_updated}`;
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
                            `onmousemove="tooltipManager.show(event, '${project}', '${suite}', '${date}')" ` +
                            `onmouseleave="tooltipManager.hide()" ` +
                            `onclick="modalManager.showSessions('${project}', '${suite}', '${date}')">` +
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
