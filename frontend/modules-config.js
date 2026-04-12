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
    // Unified dashboard runs on localhost:5000
    baseUrl: 'http://127.0.0.1:5000',
    
    // Module-specific configurations
    modules: {
        listening: {
            name: 'Listening Assessment',
            nameTamil: 'கேட்புத் திறன் மதிப்பீடு',
            enabled: true,
            // Direct URL to listening module (runs on port 5001)
            url: 'http://127.0.0.1:5001',
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
            // Direct URL to speaking module (runs on port 8001)
            url: 'http://127.0.0.1:8001',
            urlTemplate: '/speaking/index.html',
            queryParams: {},
            storageKey: 'speakingResults',
            sessionKey: 'speakingCompleted'
        },
        
        reading: {
            name: 'Reading Assessment',
            nameTamil: 'வாசித்தல் திறன் மதிப்பீடு',
            enabled: true,
            // Direct URL to reading module (runs on port 5003)
            url: 'http://127.0.0.1:5003',
            urlTemplate: '/reading/index.html',
            queryParams: {},
            storageKey: 'readingResults',
            sessionKey: 'readingCompleted'
        },
        
        writing: {
            name: 'Writing Assessment',
            nameTamil: 'எழுத்துத் திறன் மதிப்பீடு',
            enabled: true, // Now enabled
            // Direct URL to writing module (runs on port 5002)
            url: 'http://127.0.0.1:5002',
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
    
    // If direct URL is provided, use it (preferred for localhost setup)
    if (module.url) {
        // For listening: use portal URL so user goes through 5000 -> redirect to 5001 (keeps listening "on portal")
        if (moduleName === 'listening') {
            const params = new URLSearchParams();
            if (options.level !== undefined) params.set('level', options.level);
            params.set('fromFlow', '1');
            if (options.assessmentLevel) params.set('assessmentLevel', options.assessmentLevel);
            return `${MODULES_CONFIG.baseUrl}/listening?${params.toString()}`;
        }
        // Speaking, reading, writing: add fromFlow=1 when opening from assessment flow so module can show "Continue to next test"
        if (options.fromFlow && module.url) {
            const sep = module.url.includes('?') ? '&' : '?';
            return module.url + sep + 'fromFlow=1';
        }
        return module.url;
    }
    
    // Build URL from base URL and template (fallback)
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

