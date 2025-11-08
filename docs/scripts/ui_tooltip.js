// docs/scripts/ui_tooltip.js
import { CONFIG } from './config.js'; // Added import for CONFIG

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatDate(d) {
  return d.getFullYear().toString().slice(2) + '/' +
    pad2(d.getMonth() + 1) + '/' + pad2(d.getDate()) + ' - ' +
    pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
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

/**
 * Shows the tooltip for the Dashboard (single session data).
 * @param {Event} event - The mouse event.
 * @param {Object} session - The session detail object.
 */
export function showTooltip(event, session) {
  if (!session) return;
  const tooltip = document.getElementById('tooltip');
  if (!tooltip) return;

  const durationStr = computeDurationMMSS(session.start, session.end);
  const start = session.start ? new Date(session.start) : null;
  const end = session.end ? new Date(session.end) : null;

  tooltip.innerHTML = `
    <div class='tooltip-row'><strong>${session.project || 'N/A'} - ${session.suite || 'N/A'}</strong></div>
    <div class='tooltip-row'><strong>Profile: ${session.profile || 'N/A'}</strong></div>
    <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${session.test_cases || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${session.passed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${session.failed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${session.error || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${session.skipped || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${start ? formatDate(start) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>End:</span>${end ? formatDate(end) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
  `;

  positionTooltip(event, tooltip);
}

/**
 * Shows the tooltip for the Timeline (hourly aggregated data).
 * @param {Event} event - The mouse event.
 * @param {string} hourKey - The ISO key for the hour block.
 * @param {Object} envData - The aggregated data for the selected environment.
 */
export function showTimelineTooltip(event, hourKey, envData) {
    if (!envData) return;
    const tooltip = document.getElementById('tooltip');
    if (!tooltip) return;

    const hourBlockLocal = new Date(hourKey);
    const dateStr = `${pad2(hourBlockLocal.getDate())}/${pad2(hourBlockLocal.getMonth() + 1)} - ${pad2(hourBlockLocal.getHours())}:00`;

    tooltip.innerHTML = `
        <div class='tooltip-row'><strong>Hour: ${dateStr}</strong></div>
        <div class='tooltip-row'><span class='tooltip-label'>Total Sessions:</span>${envData.total}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${envData.passed}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${envData.failed}</div>
    `;

    positionTooltip(event, tooltip);
}

/**
 * Helper to position the tooltip and prevent it from going off-screen.
 */
function positionTooltip(event, tooltip) {
    tooltip.style.display = 'block';

    const padding = CONFIG.TOOLTIP_PADDING || 10;
    let top = event.pageY + padding;
    let left = event.pageX + padding;
    const rect = tooltip.getBoundingClientRect();

    if (top + rect.height > window.innerHeight) {
        top = event.pageY - rect.height - padding;
    }
    // Prevent going off left edge
    if (left < 0) left = padding;
    // Prevent going off right edge
    if (left + rect.width > window.innerWidth) {
        // Move to the left of the cursor
        left = event.pageX - rect.width - padding;
    }

    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
}

/**
 * Hides the general tooltip element.
 */
export function hideTooltip() {
  const tooltip = document.getElementById('tooltip');
  if (tooltip) {
    tooltip.style.display = 'none';
  }
}
