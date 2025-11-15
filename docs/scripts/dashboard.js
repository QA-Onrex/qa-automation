// docs/scripts/dashboard.js
import { showTooltip, hideTooltip } from './tooltip.js';
import { showSessionModal } from './modal.js';
import { openReport } from './decryptor.js';
import { CONFIG } from './config.js';

// Helper: strip up to two leading "Test Suites/" prefixes for display only
function stripLeadingTestSuites(name, maxTimes = 2) {
  try {
    if (typeof name !== 'string') return name;
    const prefix = 'Test Suites/';
    let out = name;
    let count = 0;
    while (count < maxTimes && out.startsWith(prefix)) {
      out = out.slice(prefix.length);
      count++;
    }
    return out;
  } catch {
    return name;
  }
}

export class DashboardManager {
  constructor() {
    this.data = null;
  }

  async loadData(customUrl = null) {
    const url = customUrl || CONFIG.DASHBOARD_DATA_URL;
    const options = (url === CONFIG.DASHBOARD_DATA_URL) ? { cache: 'no-store' } : {};
    const response = await fetch(url, options);
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

    if (last_updated) {
      document.getElementById('last-updated').textContent = `Last updated: ${last_updated}`;
    }

    this.renderTable(data, dates, selectedEnv);
    this.showDashboard();
  }

  renderTable(data, dates, selectedEnv) {
    // Format column dates as DD.MM
    const headerHTML = [
      '<tr><th>Test Suite</th>' +
      dates.map(d => {
        const parts = String(d).split('-'); // expect YYYY-MM-DD
        if (parts.length >= 3) {
          const dd = parts[2];
          const mm = parts[1];
          return `<th>${dd}.${mm}</th>`;
        }
        // Fallback: original substring
        return `<th>${String(d).slice(8,10)}.${String(d).slice(5,7)}</th>`;
      }).join('') +
      '</tr>'
    ];
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

          // Filter sessions by environment
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

          const latestForEnv = record.latest;
          const passed = latestForEnv.passed || 0;
          const total = latestForEnv.test_cases || 0;
          const failed = total - passed;

          // Color logic
          const hasFail = sessions.some(s => (s.failed || 0) > 0 || (s.error || 0) > 0 || (s.incomplete || 0) > 0);
          const allGreen = sessions.every(s => ((s.failed || 0) === 0 && (s.error || 0) === 0 && (s.incomplete || 0) === 0));
          let color = 'green';
          if (sessions.length === 1) {
            color = hasFail ? 'red' : 'green';
          } else {
            if (allGreen) color = 'green';
            else if (((latestForEnv.failed || 0) === 0) && ((latestForEnv.error || 0) === 0) && ((latestForEnv.incomplete || 0) === 0))
              color = 'yellow';
            else color = 'red';
          }

          // Encode session info inline
          const sessionEncoded = encodeURIComponent(JSON.stringify(latestForEnv));
          const sessionsEncoded = encodeURIComponent(JSON.stringify(sessions));

          dateCells.push(
            `<td class="${color} dashboard-cell" 
                  data-project="${encodeURIComponent(project)}" 
                  data-suite="${encodeURIComponent(suite)}" 
                  data-date="${encodeURIComponent(date)}" 
                  data-session='${sessionEncoded}' 
                  data-sessions='${sessionsEncoded}'>
                  ${passed}/${failed}
            </td>`
          );
        }

        if (suiteHasEnvMatch) {
          const displaySuite = stripLeadingTestSuites(suite, 2);
          suiteRows.push(`<tr><td class="suite-name">${displaySuite}</td>${dateCells.join('')}</tr>`);
          projectHasVisibleSuites = true;
        }
      }

      if (projectHasVisibleSuites) {
        body.push(`<tr><td class="project-header">${project}</td><td class="project-separator"></td></tr>`);
        body.push(...suiteRows);
      }
    }

    document.getElementById('table-body').innerHTML = body.join('');

    // Attach event listeners to each visible cell
    const cells = document.querySelectorAll('.dashboard-cell');
    cells.forEach(cell => {
      const project = decodeURIComponent(cell.dataset.project);
      const suite = decodeURIComponent(cell.dataset.suite);
      const date = decodeURIComponent(cell.dataset.date);
      const session = JSON.parse(decodeURIComponent(cell.dataset.session));
      const sessions = JSON.parse(decodeURIComponent(cell.dataset.sessions));

      cell.addEventListener('mousemove', e => showTooltip(e, session));
      cell.addEventListener('mouseleave', hideTooltip);

      cell.addEventListener('click', () => {
        if (window.archiveManager.currentArchive !== 'current') return;
        if (sessions.length > 1) {
          showSessionModal(project, suite, date, sessions);
        } else if (sessions.length === 1) {
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
