// docs/scripts/config.js
// Default configuration used in production and local by default
const DEFAULT_CONFIG = {
    FULL_SECRET_HASH: '232f4b3946ca2167f2f00af10db02b4108446bba13a14916cd5efa4a0ff0b756',
    DASHBOARD_DATA_URL: 'dashboard_data.json',
    ARCHIVE_INDEX_URL: 'archive/archive_index.json',
    ARCHIVE_BASE_URL: 'archive/',
    VERSION_URL: 'version.json',
    TIMELINE_DATA_URL: 'timeline_data.json',
    MAX_TOOLTIP_OFFSET: 10,
    TOOLTIP_PADDING: 10
};

// Support optional local overrides for development via window.LOCAL_CONFIG
// Create docs/scripts/local-config.js to set window.LOCAL_CONFIG = { ... }
export const CONFIG = {
    ...DEFAULT_CONFIG,
    ...(typeof window !== 'undefined' && window.LOCAL_CONFIG ? window.LOCAL_CONFIG : {})
};
