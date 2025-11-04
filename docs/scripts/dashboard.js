// docs/scripts/dashboard.js
import { showTooltip, hideTooltip } from './ui_tooltip.js';
import { handleCellClick } from './ui_modal.js';

export class DashboardManager {
  constructor() {
    this.data = null;
  }

  async loadData(customUrl = null) {
    try {
      const url = customUrl || 'dashboard_data.json';
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      this.data = await res.json();
      return this.data;
    } catch (err) {
      console.error('loadData failed', err);
      throw err;
    }
  }

  render() {
    if (!this.data) return;
    const { data, dates, last_updated } = this.data;
    if (last_updated) document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;
    this.renderTable(data, dates);
    this.showDashboard();
  }

  /**
   * Determine cell color according to:
   * - single session: green if all passed, else red
   * - multiple sessions:
   *    * all green => green
   *    * some red but last (most recent) is green => yellow
   *    * last is red => red
   *
   * sessions are expected sorted newest-first.
   */
  computeCellColor(sessions) {
    if (!Array.isArray(sessions) || sessions.length === 0) return 'empty';

    const statusOf = (s) => {
      const total = Number(s.test_cases || 0);
      const passed = Number(s.passed || 0);
      return (total > 0 && passed === total) ? 'green' : 'red';
    };

    if (sessions.length === 1) {
      return statusOf(sessions[0]) === 'green' ? 'green' : 'red';
    }

    // multiple sessions (sessions[0] is newest/last run)
    const statuses = sessions.map(statusOf);
    const allGreen = statuses.every(s => s === 'green');
    const lastStatus = statuses[0]; // newest
    if (allGreen) return 'green';
    if (lastStatus === 'green') return 'yellow';
    return 'red';
  }

  renderTable(data, dates) {
    // header
    const headerHTML = ['<tr><th>Test Suite</th>' + dates.map(d => `<th>${d.slice(5)}</th>`).join('') + '</tr>'];
    document.getElementById('table-header').innerHTML = headerHTML.join('');

    const body = [];
    const projects = Object.keys(data || {}).sort();

    for (const project of projects) {
      body.push(`<tr><td class="project-header">${project}</td>` + '<td class="project-separator"></td>'.repeat(dates.length) + '</tr>');

      const suites = Object.keys(data[project]).sort();
      for (const suite of suites) {
        const displayName = suite.replace('Test Suites/', '');
        body.push(`<tr><td class="suite-name">${displayName}</td>`);

        for (const date of dates) {
          const record = data[project][suite][date];
          if (record && record.sessions && record.sessions.length > 0) {
            // compute color from sessions
            const color = this.computeCellColor(record.sessions);
            const latest = record.latest || record.sessions[0];
            const passed = latest.passed || 0;
            const total = latest.test_cases || 0;
            const failed = (total - passed);

            // create cell with data- attributes and class dashboard-cell
            body.push(
              `<td class="${color} dashboard-cell" ` +
              `data-project="${encodeURIComponent(project)}" ` +
              `data-suite="${encodeURIComponent(suite)}" ` +
              `data-date="${encodeURIComponent(date)}">` +
              `${passed}/${failed}</td>`
            );
          } else {
            body.push('<td class="empty">–</td>');
          }
        }
        body.push('</tr>');
      }
    }

    document.getElementById('table-body').innerHTML = body.join('');

    // Attach event listeners to cells (use event delegation or per-cell)
    const cells = document.querySelectorAll('.dashboard-cell');
    cells.forEach(cell => {
      const project = decodeURIComponent(cell.dataset.project);
      const suite = decodeURIComponent(cell.dataset.suite);
      const date = decodeURIComponent(cell.dataset.date);

      cell.addEventListener('mousemove', (e) => showTooltip(e, project, suite, date));
      cell.addEventListener('mouseleave', () => hideTooltip());
      cell.addEventListener('click', () => handleCellClick(project, suite, date));
    });
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
