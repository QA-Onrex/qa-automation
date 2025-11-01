// Configuration constants
const CONFIG = {
    PASSWORD_HASH: '3718db2207be42cabda43cdfedb181ffef206cfda7ad775c7ba9e524104d2a32',
    DASHBOARD_DATA_URL: 'dashboard_data.json',
    MAX_TOOLTIP_OFFSET: 10
};

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CONFIG };
}
