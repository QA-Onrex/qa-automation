// docs/scripts/ui_tooltip.js
import { CONFIG } from './config.js';

function pad2(n) {
  return String(n).padStart(2, '0');
}

function formatDate(d) {
  return d.getFullYear().toString().slice(2) + '/' +
    pad2(d.getMonth() + 1) + '/' + pad2(d.getDate()) + ' - ' +
    pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
}

/**
 * Compute duration string MM:SS from ISO start and end strings.
 * Returns 'MM:SS' or 'N/A' on error.
 */
function computeDurationMMSS(startIso, endIso) {
  try {
    const s = new Date(startIso);
    const e = new Date(endIso);
    if (isNaN(s.getTime()) || isNaN(e.getTime())) return 'N/A';
    let sec = Math.max(0, Math.round((e - s) / 1000));
    const minutes = Math.floor(sec / 60);
    const seconds = sec % 60;
    return `${pad2(minutes)}:${pad2(seconds)}`;
  } catch (err) {
    return 'N/A';
  }
}

export function showTooltip(event, project, suite, date) {
  const dashboard = window.dashboardManager?.data;
  if (!dashboard) return;
  const record = dashboard.data?.[project]?.[suite]?.[date];
  if (!record || !record.latest) return;

  const latest = record.latest;
  const tooltip = document.getElementById('tooltip');
  const startIso = latest.start || '';
  const endIso = latest.end || '';
  const start = startIso ? new Date(startIso) : null;
  const end = endIso ? new Date(endIso) : null;

  const durationStr = computeDurationMMSS(startIso, endIso);

  tooltip.innerHTML = `
    <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${latest.profile || 'N/A'}</strong></div>
    <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${latest.test_cases || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${latest.passed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${latest.failed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${latest.error || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${latest.skipped || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${start ? formatDate(start) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>End:</span>${end ? formatDate(end) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
  `;

  tooltip.style.display = 'block';

  // Positioning
  const viewportWidth = window.innerWidth;
  const viewportHeight = window.innerHeight;
  const padding = CONFIG.TOOLTIP_PADDING || 8;

  // temporarily set to get size
  tooltip.style.left = '0px';
  tooltip.style.top = '0px';
  const rect = tooltip.getBoundingClientRect();

  let top = event.pageY + padding;
  let left = event.pageX + padding;

  if (top + rect.height > viewportHeight) {
    top = event.pageY - rect.height - padding;
  }
  if (left + rect.width > viewportWidth) {
    left = event.pageX - rect.width - padding;
  }

  top = Math.max(padding, top);
  left = Math.max(padding, left);

  tooltip.style.top = top + 'px';
  tooltip.style.left = left + 'px';
}

export function hideTooltip() {
  const tooltip = document.getElementById('tooltip');
  if (tooltip) tooltip.style.display = 'none';
}
