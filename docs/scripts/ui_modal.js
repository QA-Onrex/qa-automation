// docs/scripts/ui_modal.js
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

// -----------------------------------------------------------
// 📄 1. DASHBOARD MODAL LOGIC (Original Structure - Content + Badge separate div)
// -----------------------------------------------------------
export function showSessionModal(project, suite, date, sessions) {
  const modal = document.getElementById('session-modal');
  const sessionList = document.getElementById('session-list');
  const displayName = suite.replace('Test Suites/', '');

  // Set Modal Title based on Dashboard context
  modal.querySelector('h3').textContent = `${displayName} (${date})`;
  sessionList.innerHTML = '';
  currentSessions = sessions;

  sessions.forEach(session => {
    const div = document.createElement('div');
    div.className = 'session-item';

    // Dashboard sessions use 'start' and 'end'
    const startTime = new Date(session.start);
    const timeString = isNaN(startTime.getTime()) ? 'N/A' : startTime.toLocaleTimeString('en-GB', { hour12: false });
    const durationString = computeDurationMMSS(session.start, session.end);
    
    // Status Calculation
    const passed = session.latest?.passed || session.passed || 0;
    const failed = session.latest?.failed || session.failed || 0;
    // NOTE: This logic is for older data coming from the dashboard
    const sessionIsGreen = (failed === 0) && (passed > 0 || (session.test_cases || 0) === 0);
    let colorClass = sessionIsGreen ? 'green' : 'red';
    
    // Use the short 'profile' field
    const profileName = session.profile || 'N/A';

    // Original Dashboard Modal HTML Structure (content on left, badge on right)
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


// -----------------------------------------------------------
// 📈 2. TIMELINE MODAL LOGIC (New Structure - Suite Name + Badge nested)
// -----------------------------------------------------------
export function showTimelineModal(hourKey, hourData) {
    const modal = document.getElementById('session-modal');
    const sessionList = document.getElementById('session-list');

    // Combine and sort all sessions by start time (newest first)
    const allSessions = [...hourData.ALL.passed_details, ...hourData.ALL.failed_details]
        .sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

    // Format Hour Key for display (e.g., 2025-11-08T15:00:00Z -> 2025/11/08 - 15:00)
    const hourBlock = new Date(hourKey);
    const dateStr = `${hourBlock.getFullYear()}/${pad2(hourBlock.getMonth() + 1)}/${pad2(hourBlock.getDate())}`;
    const timeStr = `${pad2(hourBlock.getHours())}:00`;
    
    // Set Modal Title based on Timeline context
    modal.querySelector('h3').textContent = `${dateStr} - ${timeStr}`;
    sessionList.innerHTML = '';
    currentSessions = allSessions;

    allSessions.forEach(session => {
        const div = document.createElement('div');
        div.className = 'session-item';

        // Timeline sessions use 'start_time' and 'end_time'
        const startTime = new Date(session.start_time);
        const timeString = isNaN(startTime.getTime()) ? 'N/A' : startTime.toLocaleTimeString('en-GB', { hour12: false });
        const durationString = computeDurationMMSS(session.start_time, session.end_time);
        
        // Status Calculation (Timeline data has more detail)
        const passed = session.passed || 0;
        const failed = session.failed || 0;
        
        // Green status is only when all tracked failure types are zero
        const sessionIsGreen = (failed === 0 && (session.error || 0) === 0 && (session.incomplete || 0) === 0);
        let colorClass = sessionIsGreen ? 'green' : 'red';
        
        // Use the short 'profile' name from timeline data
        const profileName = session.profile || 'N/A';
        
        // Use the new 'full_name' for suite title
        const suiteName = (session.full_name || 'Test Suite Missing').replace('Test Suites/', '');

        // New Timeline Modal HTML Structure (suite name and badge are combined/nested)
        div.innerHTML = `
          <div>
            <div class="session-profile-label">Profile: ${profileName}</div>
            <div class="session-suite-title">
                ${suiteName}
                <span class="pass-fail ${colorClass}">${passed}/${failed}</span>
            </div>
            <div class="session-time-large">
                Start time: ${timeString} | Duration: ${durationString}
            </div>
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

// -----------------------------------------------------------
// 🛠️ 3. MODAL HANDLERS
// -----------------------------------------------------------
export function setupModalCloseHandlers() {
  const modal = document.getElementById('session-modal');
  if (!modal) return;
  const closeBtn = modal.querySelector('.close');
  closeBtn.addEventListener('click', () => {
    modal.style.display = 'none';
    currentSessions = [];
  });
}
