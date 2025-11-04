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
    if (!dropdown) return;
    dropdown.innerHTML = '';
    const envOptions = [
      { value: 'All', label: 'All Environments' },
      { value: 'Development', label: 'Development' },
      { value: 'Acceptance', label: 'Acceptance' }
    ];
    envOptions.forEach(o => {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      dropdown.appendChild(opt);
    });
  }

  render() {
    if (!this.data) return;
    const selectedEnv = document.getElementById('env-dropdown')?.value || 'All';
    const { data, dates, last_updated } = this.data;

    if (last_updated) document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;

    this.renderTable(data, dates, selectedEnv);
    this.showDashboard();
  }

  renderTable(data, dates, selectedEnv) {
    const headerHTML = ['<tr><th>Test Suite</th>' + dates.map(d => `<th>${d.slice(5)}</th>`).join('') + '</tr>'];
    document.getElementById('table-header').innerHTML = headerHTML.join('');

    const body = [];
    const projects = Object.keys(data || {}).sort();

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

          // sessions assumed sorted newest-first
          const latest = sessions[0];
          const passed = latest.passed || 0;
          const total = latest.test_cases || 0;
          const failed = total - passed;

          // color rules
          const hasFail = sessions.some(s => (s.failed || 0) > 0 || (s.error || 0) > 0 || (s.incomplete || 0) > 0);
          const allGreen = sessions.every(s => ((s.failed || 0) === 0 && (s.error || 0) === 0 && (s.incomplete || 0) === 0));
          let color = 'green';
          if (sessions.length === 1) {
            color = hasFail ? 'red' : 'green';
          } else {
            if (allGreen) color = 'green';
            else if (((latest.failed || 0) === 0) && ((latest.error || 0) === 0) && ((latest.incomplete || 0) === 0)) color = 'yellow';
            else color = 'red';
          }

          // produce cell with data- attributes
          dateCells.push(
            `<td class="${color} dashboard-cell" data-project="${encodeURIComponent(project)}" data-suite="${encodeURIComponent(suite)}" data-date="${encodeURIComponent(date)}" data-env="${encodeURIComponent(selectedEnv)}">${passed}/${failed}</td>`
          );
        }

        if (suiteHasEnvMatch) {
          suiteRows.push(`<tr><td class="suite-name">${suite.replace('Test Suites/', '')}</td>${dateCells.join('')}</tr>`);
          projectHasVisibleSuites = true;
        }
      }

      if (projectHasVisibleSuites) {
        body.push(`<tr><td class="project-header">${project}</td><td class="project-separator"></td></tr>`);
        body.push(...suiteRows);
      }
    }

    document.getElementById('table-body').innerHTML = body.join('');

    // attach event listeners
    const cells = document.querySelectorAll('.dashboard-cell');
    cells.forEach(cell => {
      const project = decodeURIComponent(cell.dataset.project);
      const suite = decodeURIComponent(cell.dataset.suite);
      const date = decodeURIComponent(cell.dataset.date);
      const env = decodeURIComponent(cell.dataset.env || 'All');

      cell.addEventListener('mousemove', (e) => showTooltip(e, project, suite, date));
      cell.addEventListener('mouseleave', () => hideTooltip());
      cell.addEventListener('click', () => {
        // fetch the filtered sessions for this cell and open modal or report
        const record = this.data.data?.[project]?.[suite]?.[date];
        if (!record || !record.sessions) return;

        const sessions = record.sessions.filter(s => {
          if (env === 'All') return true;
          if (env === 'Development') return s.environment?.includes('intdev');
          if (env === 'Acceptance') return s.environment?.includes('intacc');
          return false;
        });

        if (sessions.length > 1) {
          showSessionModal(project, suite, date, sessions);
        } else if (sessions.length === 1 && window.archiveManager.currentArchive === 'current') {
          // open the single session report
          openReport(sessions[0]);
        }
      });
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

// make showSessionModal available globally for any other callers (safe)
window.showSessionModal = showSessionModal;
