// docs/scripts/timeline.js
import { CONFIG } from './config.js';

// --- TIMELINE CONSTANTS ---
const MAX_CHART_HEIGHT_PX = 100; 
const MAX_SESSIONS_PER_HOUR = 20; 
const TIME_WINDOW_HOURS = 5 * 24; // 120 hours

export class TimelineManager {
    constructor() {
        this.timelineData = null;
    }

    /**
     * Renders the hourly timeline chart
     */
    async renderTimeline() {
        console.log('=== TIMELINE DEBUG START ===');
        const timelineContainer = document.getElementById('timeline-chart');
        console.log('Timeline container:', timelineContainer);
        
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
        } catch (error) {
            console.error('Failed to load timeline data:', error);
            timelineContainer.innerHTML = '<p style="color: #c62828;">Failed to load timeline data.</p>';
            return;
        }

        // 2. Generate the timeline structure
        const columnsToRender = [];
        const now = new Date();
        
        // Calculate current UTC hour in milliseconds
        const currentUTCHourMs = Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(), 
            now.getUTCDate(),
            now.getUTCHours()
        );
        
        // Track the last date shown to avoid duplicates
        let lastDateShown = null;
        
        // Generate 120 hours (5 days) of timeline
        for (let i = 0; i <= TIME_WINDOW_HOURS; i++) {
            // Calculate hour block (going backwards from current hour)
            const hourBlockUTCMs = currentUTCHourMs - i * 60 * 60 * 1000;
            const hourBlockUTC = new Date(hourBlockUTCMs);
            
            // Generate the exact hour key that matches our data structure
            const year = hourBlockUTC.getUTCFullYear();
            const month = String(hourBlockUTC.getUTCMonth() + 1).padStart(2, '0');
            const day = String(hourBlockUTC.getUTCDate()).padStart(2, '0');
            const hour = String(hourBlockUTC.getUTCHours()).padStart(2, '0');
            const hourKey = `${year}-${month}-${day}T${hour}:00:00Z`;

            // Convert to local time for display
            const hourBlockLocal = new Date(hourBlockUTCMs);
            
            // Get data for this hour
            const hourData = data[hourKey];

            // 3. Create column HTML
            let columnHtml = '';
            
            if (hourData && hourData.total > 0) {
                const { passed, failed, total } = hourData;
                const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
                
                const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
                const totalHeightPx = total_capped * sessionHeightUnit;
                
                // Calculate heights for stacked bars
                const passedHeightPx = totalHeightPx * (passed / total);
                const failedHeightPx = totalHeightPx * (failed / total);
                
                // Time label (local time)
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                
                // Date logic - show date for first column and when date changes
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                let dateLabelHtml = '';
                
                if (i === 0 || dateString !== lastDateShown) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                    lastDateShown = dateString;
                }

                // Position label above the bar, but cap it so it doesn't go below a minimum
                const minLabelTop = -25; // Minimum position (above all columns)
                const calculatedTop = MAX_CHART_HEIGHT_PX - totalHeightPx - 20;
                const labelTopPos = Math.min(calculatedTop, minLabelTop); // Use whichever is higher
                
                // Bar rendering with improved text
                columnHtml = `
                    <div class="bar-label" style="top: ${labelTopPos}px;">
                        <span class="pass-count">${passed}</span> / <span class="fail-count">${failed}</span>
                    </div>
                    <div class="stacked-bar-wrapper" style="height: ${totalHeightPx}px;">
                        <div class="bar-pass" style="height: ${passedHeightPx}px; bottom: ${failedHeightPx}px;"></div>
                        <div class="bar-fail" style="height: ${failedHeightPx}px; bottom: 0;"></div>
                    </div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
            } else {
                // Empty bar for hours with no data - NO 0/0 LABEL
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                
                // Date logic for empty columns too
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
            
            columnsToRender.push(`<div class="timeline-bar-column">${columnHtml}</div>`);
        }

        // 4. Inject columns (newest on left)
        timelineContainer.innerHTML = columnsToRender.join('');
        console.log('=== TIMELINE DEBUG END ===');
    }

    /**
     * Handles environment filter changes for the timeline
     */
    handleEnvFilterChange() {
        this.renderTimeline();
    }
}
