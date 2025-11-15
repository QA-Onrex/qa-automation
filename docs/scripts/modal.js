// docs/scripts/modal.js
import { openReport } from './decryptor.js';

let currentSessions = [];

// Helper: remove leading "Test Suites/" from any suite path for display only
// Strips up to two leading occurrences, only from the very beginning.
function stripTestSuitesPrefix(name, maxTimes = 2) {
  try {
    if (typeof name !== 'string') return name;
    let out = name;
    let count = 0;
    const prefix = 'Test Suites/';
    while (count < maxTimes && out.startsWith(prefix)) {
      out = out.slice(prefix.length);
      count++;
    }
    return out;
  } catch {
    return name;
  }
}

// Helper functions for time/duration formatting
function pad2(n) {
  return String(n).padStart(2, '0');
}

function computeDurationMMSS(startIso, endIso) {
  try {
    const s = new Date(startIso);
    const e = new Date(endIso);
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return 'N/A';
    let sec = Math.max(0, Math.round((e - s) / 1000));
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    return `${pad2(minutes)}:${pad2(seconds)}`;
  } catch {
    return 'N/A';
  }
}

export function showSessionModal(project, suite, date, sessions, options = {}) {
  const modal = document.getElementById('session-modal');
  const sessionList = document.getElementById('session-list');
  const displayName = stripTestSuitesPrefix(suite);

  // Title: use override if provided (e.g., for Timeline modal), else suite name
  const titleText = options.titleOverride || displayName;
  modal.querySelector('h3').textContent = titleText;
  sessionList.innerHTML = '';
  currentSessions = sessions;

  sessions.forEach(session => {
    const div = document.createElement('div');
    div.className = 'session-item';

    // Support sessions coming from timeline (start_time/end_time) and dashboard (start/end)
    const startIso = session.start || session.start_time;
    const endIso = session.end || session.end_time;
    const startTime = new Date(startIso);
    const timeString = isNaN(startTime.getTime()) ? 'N/A' : startTime.toLocaleTimeString('en-GB', { hour12: false });
    // Calculate the duration
    const durationString = computeDurationMMSS(startIso, endIso); 
    
    const passed = session.passed || 0;
    // Count all non-passed outcomes as failed bucket: failed + error + incomplete + skipped
    const failedBucket = (session.failed || 0) + (session.error || 0) + (session.incomplete || 0) + (session.skipped || 0);
    // Prefer explicit test_cases when available; otherwise sum from components
    const total = (typeof session.test_cases === 'number')
      ? session.test_cases
      : (passed + failedBucket);
    const effectiveFailed = Math.max(0, failedBucket || (typeof total === 'number' ? (total - passed) : 0));
    const sessionIsGreen = effectiveFailed === 0;
    let colorClass = sessionIsGreen ? 'green' : 'red';
    const profileName = session.profile || 'N/A';
    const fullName = stripTestSuitesPrefix(session.full_name || displayName);

    const suiteLineHtml = options.includeSuiteName ? `<div class="session-suite-label">${fullName}</div>` : '';
    div.innerHTML = `
      <div>
        <div class="session-profile-label">Profile: ${profileName}</div>
        ${suiteLineHtml}
        <div class="session-time-large">
            Start time: ${timeString} | Duration: ${durationString}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="pass-fail ${colorClass}">${passed}/${effectiveFailed}</span>
      </div>
    `;

    if (window.archiveManager?.currentArchive === 'current') {
      div.style.cursor = 'pointer';
      div.addEventListener('click', () => openReport(session));
    } else {
      div.style.cursor = 'default';
      div.style.opacity = '0.8';
    }

    sessionList.appendChild(div);
  });

  modal.style.display = 'block';
}

export function setupModalCloseHandlers() {
  const modal = document.getElementById('session-modal');
  if (!modal) return;
  const closeBtn = modal.querySelector('.close');
  closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    currentSessions = [];
  });
  window.addEventListener('click', e => {
    if (e.target === modal) {
      modal.style.display = 'none';
      currentSessions = [];
    }
  });
}
