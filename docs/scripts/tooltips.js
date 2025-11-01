class TooltipManager {
    constructor() {
        this.tooltip = document.getElementById('tooltip');
    }

    show(event, project, suite, date) {
        if (!window.app?.dashboard?.data) return;
        
        const record = window.app.dashboard.data.data[project]?.[suite]?.[date];
        if (!record) return;

        const start = new Date(record.latest.start);
        const end = new Date(record.latest.end);
        const formatDate = (d) => d.getFullYear().toString().slice(2) + '/' + 
            String(d.getMonth()+1).padStart(2,'0') + '/' + String(d.getDate()).padStart(2,'0') + ' - ' +
            String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0');
        
        const totalSeconds = Math.floor(record.latest.duration * 60);
        const minutes = Math.floor(totalSeconds / 60);
        const seconds = totalSeconds % 60;
        const durationStr = String(minutes).padStart(2,'0') + ':' + String(seconds).padStart(2,'0');
        
        this.tooltip.innerHTML = `
            <div class='tooltip-row'><span class='tooltip-label'>Profile:</span><strong>${record.latest.profile || 'N/A'}</strong></div>
            <div class='tooltip-row'><span class='tooltip-label'>Test Cases:</span>${record.latest.test_cases || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Passed:</span>${record.latest.passed || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Failed:</span>${record.latest.failed || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Error:</span>${record.latest.error || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Incomplete:</span>${record.latest.incomplete || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Skipped:</span>${record.latest.skipped || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Retry:</span>${record.latest.retry_count || 0}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Start:</span>${formatDate(start)}</div>
            <div class='tooltip-row'><span class='tooltip-label'>End:</span>${formatDate(end)}</div>
            <div class='tooltip-row'><span class='tooltip-label'>Duration:</span>${durationStr}</div>
        `;
        
        this.tooltip.style.display = 'block';
        this.positionTooltip(event);
    }

    positionTooltip(event) {
        const tooltipHeight = this.tooltip.offsetHeight;
        const tooltipWidth = this.tooltip.offsetWidth;
        const viewportHeight = window.innerHeight;
        const viewportWidth = window.innerWidth;

        // Default position (below and to the right of cursor)
        let top = event.pageY + CONFIG.TOOLTIP_PADDING;
        let left = event.pageX + CONFIG.TOOLTIP_PADDING;

        // Check if tooltip would go off bottom of screen
        if (top + tooltipHeight > viewportHeight) {
            top = event.pageY - tooltipHeight - CONFIG.TOOLTIP_PADDING;
        }

        // Check if tooltip would go off right of screen
        if (left + tooltipWidth > viewportWidth) {
            left = event.pageX - tooltipWidth - CONFIG.TOOLTIP_PADDING;
        }

        // Ensure tooltip doesn't go off screen edges
        top = Math.max(CONFIG.TOOLTIP_PADDING, top);
        left = Math.max(CONFIG.TOOLTIP_PADDING, left);

        this.tooltip.style.top = top + 'px';
        this.tooltip.style.left = left + 'px';
    }

    hide() {
        this.tooltip.style.display = 'none';
    }
}
