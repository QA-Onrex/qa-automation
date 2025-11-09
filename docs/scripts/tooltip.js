// docs/scripts/tooltip.js

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

export function showTooltip(event, session) {
  if (!session) return;
  const tooltip = document.getElementById('tooltip');
  if (!tooltip) return;

  const durationStr = computeDurationMMSS(session.start, session.end);
  const start = session.start ? new Date(session.start) : null;
  const end = session.end ? new Date(session.end) : null;

  tooltip.innerHTML = `
    <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${session.profile || 'N/A'}</strong></div>
    <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${session.test_cases || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${session.passed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${session.failed || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${session.error || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${session.skipped || 0}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${start ? formatDate(start) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>End:</span>${end ? formatDate(end) : 'N/A'}</div>
    <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
  `;

  tooltip.style.display = 'block';

  const padding = 8;
  let top = event.pageY + padding;
  let left = event.pageX + padding;
  const rect = tooltip.getBoundingClientRect();

  if (top + rect.height > window.innerHeight) top = event.pageY - rect.height - padding;
  if (left + rect.width > window.innerWidth) left = event.pageX - rect.width - padding;

  tooltip.style.top = `${top}px`;
  tooltip.style.left = `${left}px`;
}

export function hideTooltip() {
  const tooltip = document.getElementById('tooltip');
  if (tooltip) tooltip.style.display = 'none';
}

window.showTooltip = showTooltip;
window.hideTooltip = hideTooltip;
