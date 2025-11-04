// docs/scripts/ui_tooltip.js
import { CONFIG } from './config.js';

export function showTooltip(e, project, suite, date) {
    const dashboardData = window.dashboardManager?.data?.data;
    if (!dashboardData) return;

    const record = dashboardData[project]?.[suite]?.[date];
    if (!record?.latest) return;

    const tooltip = document.getElementById('tooltip');
    const start = new Date(record.latest.start);
    const end = new Date(record.latest.end);

    const formatDate = (d) => 
        d.getFullYear().toString().slice(2) + '/' +
        String(d.getMonth()+1).padStart(2,'0') + '/' +
        String(d.getDate()).padStart(2,'0') + ' - ' +
        String(d.getHours()).padStart(2,'0') + ':' +
        String(d.getMinutes()).padStart(2,'0') + ':' +
        String(d.getSeconds()).padStart(2,'0');

    tooltip.innerHTML = `
        <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${record.latest.profile || 'N/A'}</strong></div>
        <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${record.latest.test_cases || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${record.latest.passed || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${record.latest.failed || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${record.latest.error || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${record.latest.skipped || 0}</div>
        <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${formatDate(start)}</div>
        <div class='tooltip-row'><span class='tooltip-label'>End:</span>${formatDate(end)}</div>
    `;

    tooltip.style.display = 'block';

    // Position tooltip smartly to stay inside viewport
    const rect = tooltip.getBoundingClientRect();
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;

    let top = e.pageY + CONFIG.TOOLTIP_PADDING;
    let left = e.pageX + CONFIG.TOOLTIP_PADDING;

    if (top + rect.height > viewportHeight) top = e.pageY - rect.height - CONFIG.TOOLTIP_PADDING;
    if (left + rect.width > viewportWidth) left = e.pageX - rect.width - CONFIG.TOOLTIP_PADDING;

    tooltip.style.top = Math.max(CONFIG.TOOLTIP_PADDING, top) + 'px';
    tooltip.style.left = Math.max(CONFIG.TOOLTIP_PADDING, left) + 'px';
}

export function hideTooltip() {
    document.getElementById('tooltip').style.display = 'none';
}
