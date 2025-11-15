// docs/scripts/timeline.js
import { CONFIG } from './config.js';
import { showTimelineTooltip, hideTooltip } from './tooltip.js';
import { showSessionModal } from './modal.js';

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
        } catch (error) {
            console.error('Failed to load timeline data:', error);
            timelineContainer.innerHTML = '<p style="color: #c62828;">Failed to load timeline data.</p>';
            return;
        }

        // 2. Get selected environment filter (already mapped to data key)
        const filterKey = this.getSelectedEnvironment();

        // 3. Generate the timeline structure
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
            
            // Get data for this hour and apply environment filter
            const hourData = data[hourKey];
            const envData = hourData ? hourData[filterKey] : null;

            // 4. Create column HTML
            let columnHtml = '';
            
            if (envData && envData.total > 0) {
                const { passed, failed, total } = envData;
                const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
                
                const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
                const totalHeightPx = total_capped * sessionHeightUnit;
                
                // Calculate heights for stacked bars - FAILED at bottom, PASSED on top
                const failedHeightPx = totalHeightPx * (failed / total);
                const passedHeightPx = totalHeightPx * (passed / total);
                
                // Time label (local time)
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                
                // Date logic - show date for first column and when date changes
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                let dateLabelHtml = '';
                
                if (i === 0 || dateString !== lastDateShown) {
                    dateLabelHtml = `<div class="timeline-date-label">${dateString}</div>`;
                    lastDateShown = dateString;
                }
                
                // Bar rendering - bars grow from bottom, failed first then passed on top
                columnHtml = `
                    <div class="bar-label">
                        <span class="pass-count">${passed}</span> / <span class="fail-count">${failed}</span>
                    </div>
                    <div class="stacked-bar-wrapper" style="height: ${totalHeightPx}px;">
                        <div class="bar-fail" style="height: ${failedHeightPx}px;"></div>
                        <div class="bar-pass" style="height: ${passedHeightPx}px; bottom: ${failedHeightPx}px;"></div>
                    </div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
                const compactEnv = {
                    passed: envData.passed || 0,
                    failed: envData.failed || 0,
                    passed_details: Array.isArray(envData.passed_details) ? envData.passed_details : [],
                    failed_details: Array.isArray(envData.failed_details) ? envData.failed_details : []
                };
                const dataAttr = encodeURIComponent(JSON.stringify(compactEnv));
                columnsToRender.push(`<div class="timeline-bar-column" data-env="${dataAttr}" data-hourms="${hourBlockLocal.getTime()}">${columnHtml}</div>`);
                continue;
            } else {
                // Empty bar for hours with no data - NO NUMBERS
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

        // 5. Inject columns (newest on left)
        timelineContainer.innerHTML = columnsToRender.join('');

        // 6. Attach hover tooltips for columns with data
        const cols = timelineContainer.querySelectorAll('.timeline-bar-column[data-env]');
        cols.forEach(col => {
            const hourMs = Number(col.getAttribute('data-hourms'));
            let envData;
            try {
                envData = JSON.parse(decodeURIComponent(col.getAttribute('data-env')));
            } catch {
                envData = null;
            }
            if (!envData) return;
            col.addEventListener('mousemove', (e) => {
                const d = new Date(hourMs);
                showTimelineTooltip(e, d, envData);
            });
            col.addEventListener('mouseleave', () => hideTooltip());

            // Click to open modal with sessions list for this hour
            col.addEventListener('click', () => {
                const hourLocal = new Date(hourMs);
                const y = hourLocal.getFullYear();
                const m = String(hourLocal.getMonth() + 1).padStart(2, '0');
                const d = String(hourLocal.getDate()).padStart(2, '0');
                const hh = String(hourLocal.getHours()).padStart(2, '0');
                const title = `${y}/${m}/${d} - ${hh}:00`;

                const passedList = Array.isArray(envData.passed_details) ? envData.passed_details : [];
                const failedList = Array.isArray(envData.failed_details) ? envData.failed_details : [];
                const sessions = [...passedList, ...failedList];

                // If there are no sessions, do nothing
                if (!sessions.length) return;

                // Use generic identifiers for project/suite, since timeline aggregates across suites
                const project = 'Timeline';
                const suite = 'Timeline Hour';
                const date = title;

                showSessionModal(project, suite, date, sessions, { titleOverride: title, includeSuiteName: true });
            });
        });
    }

    /**
     * Handles environment filter changes for the timeline
     */
    handleEnvFilterChange() {
        this.renderTimeline();
    }
}
