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
     * Renders the hourly timeline chart based on the selected environment filter.
     */
    async renderTimeline() {
        console.log('=== TIMELINE DEBUG START ===');
        const timelineContainer = document.getElementById('timeline-chart');
        console.log('Timeline container:', timelineContainer);
        console.log('Container visible:', timelineContainer?.offsetParent !== null);
        
        if (!timelineContainer) {
            console.error('No timeline container found!');
            return;
        }
        
        timelineContainer.innerHTML = ''; 

        // 1. Fetch timeline data with cache bust
        let data;
        try {
            const response = await fetch(CONFIG.TIMELINE_DATA_URL + '?t=' + Date.now());
            console.log('Fetch response status:', response.status);
            if (!response.ok) throw new Error('Timeline data not found');
            data = await response.json();
            console.log('=== TIMELINE DATA ANALYSIS ===');
            console.log('Data loaded:', data);
            console.log('Data type:', typeof data);
            console.log('Is array?:', Array.isArray(data));
            console.log('Keys:', Object.keys(data));
            console.log('Key count:', Object.keys(data).length);
            
            // Test direct access
            const testKey = '2025-11-07T16:00:00Z';
            console.log(`Direct access test [${testKey}]:`, data[testKey]);
            console.log('Stringified data:', JSON.stringify(data));
            
        } catch (error) {
            console.error('Failed to load timeline data:', error);
            timelineContainer.innerHTML = '<p style="color: #c62828;">Failed to load timeline data.</p>';
            return;
        }

        // Store for later use
        this.timelineData = data;

        // 2. Generate the timeline structure
        const columnsToRender = [];
        const now = new Date();
        
        console.log('=== TIME CALCULATION DEBUG ===');
        console.log('Local now:', now.toString());
        console.log('UTC now:', now.toUTCString());
        
        // Calculate current UTC hour in milliseconds
        const currentUTCHourMs = Date.UTC(
            now.getUTCFullYear(),
            now.getUTCMonth(), 
            now.getUTCDate(),
            now.getUTCHours()
        );
        console.log('Current UTC hour ms:', currentUTCHourMs);
        
        // Test our specific data hour
        const testDataHour = new Date('2025-11-07T16:00:00Z');
        const testHourMs = Date.UTC(2025, 10, 7, 16); // Note: month is 0-based
        console.log('Test data hour (2025-11-07T16:00:00Z):', testDataHour.toUTCString());
        console.log('Test hour ms:', testHourMs);
        
        // Generate 120 hours (5 days) of timeline
        console.log('=== COLUMN GENERATION DEBUG ===');
        let dataFound = false;
        
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
            
            // SPECIAL DEBUG: Check if this is our test hour
            if (hourKey === '2025-11-07T16:00:00Z') {
                console.log('=== TEST HOUR FOUND ===');
                console.log('Test hour key:', hourKey);
                console.log('Hour data:', hourData);
                console.log('Direct lookup:', data['2025-11-07T16:00:00Z']);
                console.log('All keys available:', Object.keys(data));
            }
            
            if (hourData) {
                dataFound = true;
                console.log(`DATA FOUND at ${hourKey}:`, hourData);
            }

            // 3. Create column HTML
            let columnHtml = '';
            
            if (hourData && hourData.total > 0) {
                console.log(`Rendering bar for ${hourKey}: ${hourData.passed}/${hourData.failed}`);
                const { passed, failed, total } = hourData;
                const total_capped = Math.min(total, MAX_SESSIONS_PER_HOUR);
                
                const sessionHeightUnit = MAX_CHART_HEIGHT_PX / MAX_SESSIONS_PER_HOUR;
                const totalHeightPx = total_capped * sessionHeightUnit;
                
                // Calculate heights for stacked bars
                const passedHeightPx = totalHeightPx * (passed / total);
                const failedHeightPx = totalHeightPx * (failed / total);
                
                // Time label (local time)
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                
                // Date label
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                const dateLabelHtml = i === 0 ? `<div class="timeline-date-label">${dateString}</div>` : '';
                
                // Position label above the bar
                const labelTopPos = MAX_CHART_HEIGHT_PX - totalHeightPx - 15;

                // Bar rendering
                columnHtml = `
                    <div class="bar-label" style="top: ${labelTopPos}px;">
                        <span class="pass-count">${passed}</span>/<span class="fail-count">${failed}</span>
                    </div>
                    <div class="stacked-bar-wrapper" style="height: ${totalHeightPx}px;">
                        <div class="bar-pass" style="height: ${passedHeightPx}px; bottom: ${failedHeightPx}px;"></div>
                        <div class="bar-fail" style="height: ${failedHeightPx}px; bottom: 0;"></div>
                    </div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
            } else {
                // Empty bar for hours with no data
                const hourLabel = String(hourBlockLocal.getHours()).padStart(2, '0') + ':00';
                const dateString = `${String(hourBlockLocal.getDate()).padStart(2, '0')}.${String(hourBlockLocal.getMonth() + 1).padStart(2, '0')}`;
                const dateLabelHtml = i === 0 ? `<div class="timeline-date-label">${dateString}</div>` : '';
                
                columnHtml = `
                    <div class="bar-label" style="top: 5px; color: #666;">
                        0/0
                    </div>
                    <div class="stacked-bar-wrapper" style="height: ${MAX_CHART_HEIGHT_PX}px;"></div>
                    <div class="timeline-hour-label">${hourLabel}</div>
                    ${dateLabelHtml}
                `;
            }
            
            columnsToRender.push(`<div class="timeline-bar-column">${columnHtml}</div>`);
        }

        console.log('=== FINAL DEBUG SUMMARY ===');
        console.log('Data found during loop:', dataFound);
        console.log('Total columns generated:', columnsToRender.length);
        console.log('First column HTML:', columnsToRender[0]?.substring(0, 100) + '...');

        // 4. Inject columns (newest on left)
        timelineContainer.innerHTML = columnsToRender.join('');
        console.log('Timeline container innerHTML length:', timelineContainer.innerHTML.length);
        console.log('=== TIMELINE DEBUG END ===');
    }

    /**
     * Handles environment filter changes for the timeline
     */
    handleEnvFilterChange() {
        this.renderTimeline();
    }
}
