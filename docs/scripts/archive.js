// docs/scripts/archive.js
import { CONFIG } from './config.js';

export class ArchiveManager {
    constructor() {
        this.archives = [];
        this.currentArchive = 'current';
    }

    async loadArchiveIndex() {
        try {
            const res = await fetch(CONFIG.ARCHIVE_INDEX_URL);
            if (!res.ok) throw new Error('Failed to load archive index');
            this.archives = await res.json();
            return this.archives;
        } catch (e) {
            console.error('Archive load error:', e);
            this.archives = [];
            return [];
        }
    }

    formatArchiveDisplayName(id) {
        if (id === 'current') return 'Current (Live)';
        const [year, month] = id.split('_');
        const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${monthNames[parseInt(month) - 1]} ${year}`;
    }

    getArchiveFileName(id) {
        return id === 'current'
            ? CONFIG.DASHBOARD_DATA_URL
            : `${CONFIG.ARCHIVE_BASE_URL}${id}_dashboard_data.json`;
    }
}
