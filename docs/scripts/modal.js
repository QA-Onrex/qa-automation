// docs/scripts/modal.js
import { openReport } from './decryptor.js';

let currentSessions = [];

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

export function showSessionModal(project, suite, date, sessions) {
  const modal = document.getElementById('session-modal');
  const sessionList = document.getElementById('session-list');
  const displayName = suite.replace('Test Suites/', '');

  modal.querySelector('h3').textContent = displayName;
  sessionList.innerHTML = '';
  currentSessions = sessions;

  sessions.forEach(session => {
    const div = document.createElement('div');
    div.className = 'session-item';

    const startTime = new Date(session.start);
    const timeString = isNaN(startTime.getTime()) ? 'N/A' : startTime.toLocaleTimeString('en-GB', { hour12: false });
    // Calculate the duration
    const durationString = computeDurationMMSS(session.start, session.end); 
    
    const passed = session.passed || 0;
    const total = session.test_cases || 0;
    const failed = total - passed;
    const sessionIsGreen = (typeof session.test_cases === 'number') && ((session.passed || 0) === (session.test_cases || 0));
    let colorClass = sessionIsGreen ? 'green' : 'red';
    const profileName = session.profile || 'N/A';

    div.innerHTML = `
      <div>
        <div class="session-profile-label">Profile: ${profileName}</div>
        <div class="session-time-large">
            Start time: ${timeString} | Duration: ${durationString}
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:10px;">
        <span class="pass-fail ${colorClass}">${passed}/${failed}</span>
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
