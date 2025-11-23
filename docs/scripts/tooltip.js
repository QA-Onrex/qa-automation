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
        <div class='tooltip-row'><span class='tooltip-label'>Incomplete:</span>${session.incomplete || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${session.skipped || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${start ? formatDate(start) : 'N/A'}</div>
        <div class='tooltip-row'><span class='tooltip-label'>End:</span>${end ? formatDate(end) : 'N/A'}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
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

// --- Timeline tooltip (hour summary + sessions list) ---
function formatYMD(hourDate) {
    const y = hourDate.getFullYear();
    const m = pad2(hourDate.getMonth() + 1);
    const d = pad2(hourDate.getDate());
    return `${y}/${m}/${d}`;
}

function formatHM(date) {
    return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function showTimelineTooltip(event, hourLocalDate, envData) {
    if (!envData || !hourLocalDate) return;
    const tooltip = document.getElementById('tooltip');
    if (!tooltip) return;

    // Title and summary
    const titleLine = `${formatYMD(hourLocalDate)} - ${pad2(hourLocalDate.getHours())}:00`;
    const summaryLine = `✅ ${envData.passed || 0} passed | ❌ ${envData.failed || 0} failed`;

    // Build sessions list (combine passed and failed details)
    const passedList = Array.isArray(envData.passed_details) ? envData.passed_details : [];
    const failedList = Array.isArray(envData.failed_details) ? envData.failed_details : [];
    const allSessions = [...passedList, ...failedList];

    // Sort by start_time descending
    allSessions.sort((a, b) => new Date(b.start_time) - new Date(a.start_time));

    const sessionLines = allSessions.map(s => {
        const start = s.start_time ? new Date(s.start_time) : null;
        const hm = start ? formatHM(start) : '--:--';
        const fullName = s.full_name || 'Unknown';
        const shortName = fullName.includes('/') ? fullName.split('/').pop() : fullName;
        // Treat Skipped as a failure along with Failed, Error, and Incomplete
        const isPass = (s.failed || 0) === 0 && (s.error || 0) === 0 && (s.incomplete || 0) === 0 && (s.skipped || 0) === 0;
        const mark = isPass ? '✅' : '❌';
        return `<div class='tooltip-row'>${hm} ${shortName} ${mark}</div>`;
    }).join('');

    tooltip.innerHTML = `
        <div class='tooltip-row' style='font-weight:600;'>${titleLine}</div>
        <div class='tooltip-row'>${summaryLine}</div>
        ${sessionLines ? "<div class='tooltip-row'>&nbsp;</div>" + sessionLines : ''}
    `;

    tooltip.style.display = 'block';

    // Position similarly to showTooltip
    const padding = 8;
    let top = event.pageY + padding;
    let left = event.pageX + padding;
    const rect = tooltip.getBoundingClientRect();
    if (top + rect.height > window.innerHeight) top = event.pageY - rect.height - padding;
    if (left + rect.width > window.innerWidth) left = event.pageX - rect.width - padding;
    tooltip.style.top = `${top}px`;
    tooltip.style.left = `${left}px`;
}

window.showTimelineTooltip = showTimelineTooltip;
