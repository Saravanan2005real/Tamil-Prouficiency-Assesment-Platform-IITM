/**
 * Modules Configuration File
 * 
 * This file contains all the configuration for the 4 language assessment modules:
 * - Listening
 * - Speaking
 * - Reading
 * - Writing
 * 
 * Update the URLs and settings here to integrate your modules.
 */

const MODULES_CONFIG = {
    // Base URL configuration
    // If all modules are on the same server, use a base URL
    // If modules are on different servers, set individual URLs for each module
    baseUrl: 'http://localhost:5000',
    
    // Module-specific configurations
    modules: {
        listening: {
            name: 'Listening Assessment',
            nameTamil: 'கேட்புத் திறன் மதிப்பீடு',
            enabled: true,
            // If empty, will use: baseUrl + '/listening/index.html'
            // If set, will use this URL directly
            url: '',
            // URL template - use {level} as placeholder for dynamic level
            urlTemplate: '/listening/index.html?level={level}',
            // Query parameters to pass
            queryParams: {
                level: '1' // Default level
            },
            // Storage keys for results
            storageKey: 'listeningResults',
            sessionKey: 'listeningCompleted'
        },
        
        speaking: {
            name: 'Speaking Assessment',
            nameTamil: 'பேச்சுத் திறன் மதிப்பீடு',
            enabled: true,
            url: '',
            urlTemplate: '/speaking/index.html',
            queryParams: {},
            storageKey: 'speakingResults',
            sessionKey: 'speakingCompleted'
        },
        
        reading: {
            name: 'Reading Assessment',
            nameTamil: 'வாசித்தல் திறன் மதிப்பீடு',
            enabled: true,
            url: '',
            urlTemplate: '/reading/index.html',
            queryParams: {},
            storageKey: 'readingResults',
            sessionKey: 'readingCompleted'
        },
        
        writing: {
            name: 'Writing Assessment',
            nameTamil: 'எழுத்துத் திறன் மதிப்பீடு',
            enabled: false, // Set to true when writing module is ready
            url: '',
            urlTemplate: '/writing/index.html',
            queryParams: {},
            storageKey: 'writingResults',
            sessionKey: 'writingCompleted'
        }
    },
    
    // Level configurations - which modules are included in each level
    levels: {
        basic: ['listening', 'speaking'],
        intermediate: ['listening', 'speaking', 'reading'],
        advanced: ['listening', 'speaking', 'reading', 'writing']
    },
    
    // Test flow settings
    flow: {
        // Redirect URL parameters to pass completion status
        useUrlParams: true,
        // URL parameter names
        paramNames: {
            listeningDone: 'listeningDone',
            speakingDone: 'speakingDone',
            readingDone: 'readingDone',
            writingDone: 'writingDone'
        }
    }
};

/**
 * Helper function to get module URL
 * @param {string} moduleName - Name of the module (listening, speaking, reading, writing)
 * @param {object} options - Additional options (e.g., {level: 2})
 * @returns {string} Complete URL for the module
 */
function getModuleUrl(moduleName, options = {}) {
    const module = MODULES_CONFIG.modules[moduleName];
    
    if (!module) {
        console.error(`Module ${moduleName} not found in configuration`);
        return '';
    }
    
    if (!module.enabled) {
        console.warn(`Module ${moduleName} is not enabled`);
        return '';
    }
    
    // If direct URL is provided, use it
    if (module.url) {
        return module.url;
    }
    
    // Build URL from base URL and template
    let url = MODULES_CONFIG.baseUrl + module.urlTemplate;
    
    // Replace placeholders in template (e.g., {level})
    if (options.level !== undefined) {
        url = url.replace('{level}', options.level);
    } else if (module.queryParams.level) {
        url = url.replace('{level}', module.queryParams.level);
    }
    
    // Add query parameters
    const queryParams = { ...module.queryParams, ...options };
    const queryString = Object.keys(queryParams)
        .filter(key => queryParams[key] !== undefined && queryParams[key] !== null)
        .map(key => `${encodeURIComponent(key)}=${encodeURIComponent(queryParams[key])}`)
        .join('&');
    
    if (queryString && !url.includes('?')) {
        url += '?' + queryString;
    } else if (queryString) {
        url += '&' + queryString;
    }
    
    return url;
}

/**
 * Check if a module is enabled
 * @param {string} moduleName - Name of the module
 * @returns {boolean} True if enabled, false otherwise
 */
function isModuleEnabled(moduleName) {
    return MODULES_CONFIG.modules[moduleName]?.enabled === true;
}

/**
 * Get modules for a specific level
 * @param {string} level - Level name (basic, intermediate, advanced)
 * @returns {Array} Array of module names
 */
function getModulesForLevel(level) {
    return MODULES_CONFIG.levels[level] || [];
}

/**
 * Get module configuration
 * @param {string} moduleName - Name of the module
 * @returns {object} Module configuration object
 */
function getModuleConfig(moduleName) {
    return MODULES_CONFIG.modules[moduleName] || null;
}

// Make functions available globally
if (typeof window !== 'undefined') {
    window.MODULES_CONFIG = MODULES_CONFIG;
    window.getModuleUrl = getModuleUrl;
    window.isModuleEnabled = isModuleEnabled;
    window.getModulesForLevel = getModulesForLevel;
    window.getModuleConfig = getModuleConfig;
}

