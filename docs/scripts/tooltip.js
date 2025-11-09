// docs/scripts/tooltip.js

function pad2(n) {
    return String(n).padStart(2, '0');
}

function formatDate(d) {
    // Formats date as YY/MM/DD - HH:MM:SS
    return d.getFullYear().toString().slice(2) + '/' +
        pad2(d.getMonth() + 1) + '/' + pad2(d.getDate()) + ' - ' +
        pad2(d.getHours()) + ':' + pad2(d.getMinutes()) + ':' + pad2(d.getSeconds());
}

function computeDurationMMSS(startIso, endIso) {
    try {
        const s = new Date(startIso);
        const e = new Date(endIso);
        if (isNaN(s.getTime()) || isNaN(e.getTime())) return 'N/A';
        // Calculate duration in seconds
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

    // Logic to display the session count, which is now provided by the Python script
    let multipleSessionsHtml = '';
    if (session.sessionCount && session.sessionCount > 1) {
        // Add a blank line for separation (using non-breaking space)
        // followed by the Total Runs count.
        multipleSessionsHtml = `
            <div class='tooltip-row'>&nbsp;</div>
            <div class='tooltip-row'>
                <span class='tooltip-label'>Total Runs:</span>
                <strong>${session.sessionCount}</strong>
            </div>
        `;
    }

    // Build the main tooltip content using the augmented HTML
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
        <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${session.sessionCount || 0}</div>
        ${multipleSessionsHtml}
    `;

    tooltip.style.display = 'block';

    // Positioning logic to keep the tooltip visible
    const padding = 8;
    let top = event.pageY + padding;
    let left = event.pageX + padding;
    const rect = tooltip.getBoundingClientRect();

    // Adjust vertical position if it goes off the bottom of the screen
    if (top + rect.height > window.innerHeight) top = event.pageY - rect.height - padding;
    // Adjust horizontal position if it goes off the right of the screen
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
