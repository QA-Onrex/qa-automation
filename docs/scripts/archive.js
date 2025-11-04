// docs/scripts/archive.js
import { CONFIG } from './config.js';

export class ArchiveManager {
    constructor() {
        this.archives = [];
        this.currentArchive = 'current';
    }

    async loadArchiveIndex() {
        try {
            const response = await fetch(CONFIG.ARCHIVE_INDEX_URL);
            if (!response.ok) throw new Error('Failed to load archive index');
            this.archives = await response.json();
        } catch (error) {
            console.error('Error loading archive index:', error);
            this.archives = [];
        }
    }

    populateDropdownSelector() {
        const dropdown = document.getElementById('archive-dropdown');
        dropdown.innerHTML = '<option value="current">Current (Live)</option>';

        this.archives.forEach(archiveId => {
            const option = document.createElement('option');
            option.value = archiveId;
            option.textContent = this.formatArchiveDisplayName(archiveId);
            dropdown.appendChild(option);
        });
    }

    formatArchiveDisplayName(archiveId) {
        if (archiveId === 'current') return 'Current (Live)';
        const [year, month] = archiveId.split('_');
        const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    }

    getArchiveFileName(archiveId) {
        if (archiveId === 'current') return CONFIG.DASHBOARD_DATA_URL;
        return `${CONFIG.ARCHIVE_BASE_URL}${archiveId}_dashboard_data.json`;
    }
}
