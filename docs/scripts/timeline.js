// docs/scripts/timeline.js
import { CONFIG } from './config.js';
// Import the new timeline functions
import { showTimelineTooltip, hideTooltip } from './ui_tooltip.js';
import { showTimelineModal } from './ui_modal.js';

// --- TIMELINE CONSTANTS ---
const MAX_CHART_HEIGHT_PX = 100;
const MAX_SESSIONS_PER_HOUR = 20; 
const TIME_WINDOW_HOURS = 5 * 24; // 120 hours

export class TimelineManager {
    constructor() {
        this.timelineData = null;
    }

    /**
     * Gets the currently selected environment filter and maps to data keys
     */
    getSelectedEnvironment() {
        const envFilterElement = document.getElementById('env-dropdown'); 
        const selectedValue = envFilterElement ? envFilterElement.value : 'All';
        
        // Map dropdown values to data keys
        switch(selectedValue) {
            case 'All': return 'ALL';
            case 'Development': return 'intdev';
            case 'Acceptance': return 'intacc';
            default: return 'ALL';
        }
    }

    /**
     * Renders the hourly timeline chart with environment filtering
     */
    async renderTimeline() {
        const timelineContainer = document.getElementById('timeline-chart');
        
        if (!timelineContainer) {
            console.error('No timeline container found!');
            return;
        }
        
        timelineContainer.innerHTML = ''; 

        // 1. Fetch timeline data with cache bust
        let data;
        try {
            const response = await fetch(CONFIG.TIMELINE_DATA_URL + '?t=' + Date.now());
            if (!response.ok) throw new Error('Timeline data not found');
            data = await response.json();
            this.timelineData = data;
        } catch (error) {
            console.error('Error fetching timeline data:', error);
            timelineContainer.innerHTML = '<div style="color: #f44336; padding: 20px;">Could not load timeline data.</div>';
            return;
        }

        const selectedEnv = this.getSelectedEnvironment();
        const nowUtc = new Date(Date.now()).toISOString().replace(/\.\d{3}/, '').replace('Z', '+00:00');
        const now = new Date(nowUtc);
        
        const columnsToRender = [];
        let lastDateShown = '';
        
        // Loop backwards from the current hour for TIME_WINDOW_HOURS
        for (let i = 0; i < TIME_WINDOW_HOURS; i++) {
            // Calculate the hour block start time (UTC)
            const hourBlockUtc = new Date(now);
            hourBlockUtc.setUTCHours(now.getUTCHours() - i, 0, 0, 0); 
            
            // Generate the ISO key (matches Python script format)
            const hourKey = hourBlockUtc.toISOString().replace('+00:00', 'Z'); 
            
            // Get the data for the current hour, or an empty object
            const hourData = this.timelineData[hourKey];
            const envData = hourData ? hourData[selectedEnv] : null;
            
            let columnHtml = '';
            
            // Convert UTC key to local time for display labels
            const hourBlockLocal = new Date(hourKey);

            if (envData && envData.total > 0) {
                const { total, passed, failed } = envData;
                
                // Calculate heights based on total sessions
                const ratio = Math.min(total / MAX_SESSIONS_PER_HOUR, 1);
                const chartHeight = ratio * MAX_CHART_HEIGHT_PX;
                
                const passHeight = (passed / total) * chartHeight;
                const failHeight = (failed / total) * chartHeight;
                
                // Format display labels
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                
                let dateLabelHtml = '';
                if (i === 0 || dateString !== lastDateShown) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                    lastDateShown = dateString;
                }
                
                columnHtml = `
                    <div class="bar-label">
                        <span class="pass-count">${passed}</span>/<span class="fail-count">${failed}</span>
                    </div>
                    <div class="stacked-bar-wrapper" style="height: ${MAX_CHART_HEIGHT_PX}px;">
                        <div class="bar-fail" style="height: ${failHeight}px; bottom: 0;"></div>
                        <div class="bar-pass" style="height: ${passHeight}px; bottom: ${failHeight}px;"></div>
                    </div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
            } else {
                // Empty bar for hours with no data
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                let dateLabelHtml = '';
                
                if (i === 0 || dateString !== lastDateShown) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                    lastDateShown = dateString;
                }
                
                columnHtml = `
                    <div class="stacked-bar-wrapper" style="height: ${MAX_CHART_HEIGHT_PX}px;"></div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
            }
            
            // Use data attributes to store the relevant key for event listeners
            columnsToRender.push(
                `<div class="timeline-bar-column" data-hour-key="${hourKey}">
                    ${columnHtml}
                </div>`
            );
        }

        // 5. Inject columns (newest on left)
        timelineContainer.innerHTML = columnsToRender.join('');

        // 6. Attach Event Listeners to all columns
        document.querySelectorAll('.timeline-bar-column').forEach(column => {
            const hourKey = column.dataset.hourKey;
            if (!hourKey) return; // Skip columns without a key
            
            const hourData = this.timelineData[hourKey];

            // Attach listeners only if data exists for the hour (or to the whole column)
            if (hourData) {
                // TOOLTIP: Attach mouseover/mouseleave to the entire column
                // Note: The tooltip content is generated based on ALL sessions, 
                // but the event should be triggered by any element in the column.
                column.addEventListener('mousemove', e => {
                    // Check if mouse is over the bar wrapper to prevent showing on just the labels
                    if (e.target.closest('.stacked-bar-wrapper')) {
                        showTimelineTooltip(e, hourKey, hourData[this.getSelectedEnvironment()]);
                    } else {
                        hideTooltip();
                    }
                });
                column.addEventListener('mouseleave', hideTooltip);

                // MODAL: Attach click listener to the entire column
                column.addEventListener('click', () => {
                    // Use ALL environment data for the modal, regardless of the active chart filter
                    showTimelineModal(hourKey, hourData);
                });
            } else {
                // For empty columns, ensure tooltip is hidden if accidentally triggered
                column.addEventListener('mousemove', hideTooltip);
                column.addEventListener('mouseleave', hideTooltip);
            }
        });
    }

    /**
     * Handles environment filter changes for the timeline
     */
    handleEnvFilterChange() {
        this.renderTimeline();
    }
}
