# Modules Integration Guide

This guide explains how to integrate and configure the 4 language assessment modules (Listening, Speaking, Reading, Writing) into the unified assessment platform.

## Overview

The project uses a configuration-based approach to integrate modules. All module URLs and settings are centralized in `modules-config.js`, making it easy to connect modules running on different servers or update URLs when needed.

## File Structure

- **`modules-config.js`** - Configuration file for all modules
- **`modules-integration.js`** - Integration utilities and helpers
- **`assessment-flow.html`** - Main assessment flow page (uses the configuration)

## Configuration (`modules-config.js`)

### Base URL Setup

```javascript
baseUrl: 'http://localhost:5000'
```

If all modules are on the same server, set the base URL here. If modules are on different servers, you can set individual URLs for each module (see below).

### Module Configuration

Each module has the following configuration options:

```javascript
listening: {
    name: 'Listening Assessment',           // Display name
    nameTamil: 'கேட்புத் திறன் மதிப்பீடு',  // Tamil display name
    enabled: true,                          // Enable/disable module
    url: '',                                // Direct URL (optional)
    urlTemplate: '/listening/index.html?level={level}', // URL template
    queryParams: { level: '1' },           // Default query parameters
    storageKey: 'listeningResults',        // localStorage key for results
    sessionKey: 'listeningCompleted'       // sessionStorage key for completion
}
```

### Setting Module URLs

#### Option 1: All modules on the same server

```javascript
baseUrl: 'http://localhost:5000'
// Modules will use: baseUrl + urlTemplate
```

#### Option 2: Individual URLs for each module

```javascript
listening: {
    url: 'http://localhost:5000/listening/index.html',
    // urlTemplate will be ignored if url is set
}
speaking: {
    url: 'http://localhost:3000/speaking/index.html',
}
```

#### Option 3: Mixed (some on same server, some different)

```javascript
baseUrl: 'http://localhost:5000'

listening: {
    url: '',  // Will use baseUrl + urlTemplate
    urlTemplate: '/listening/index.html'
}
speaking: {
    url: 'http://different-server.com/speaking/index.html'  // Uses direct URL
}
```

### Level Configuration

Define which modules are included in each assessment level:

```javascript
levels: {
    basic: ['listening', 'speaking'],
    intermediate: ['listening', 'speaking', 'reading'],
    advanced: ['listening', 'speaking', 'reading', 'writing']
}
```

## Adding a New Module

1. **Update `modules-config.js`**:
   - Add your module configuration in the `modules` object
   - Set `enabled: true` when ready
   - Configure the URL and template

2. **Update level configuration** (if needed):
   - Add the module name to the appropriate level array

3. **Add module rules** (optional):
   - In `assessment-flow.html`, add rules in the `showRules()` function

4. **Test the integration**:
   - Enable the module in config
   - Test the flow from start to finish

## Enabling/Disabling Modules

To temporarily disable a module without removing it:

```javascript
writing: {
    enabled: false,  // Module will be skipped in the flow
    // ... other config
}
```

## Integration with Module Pages

### For Module Developers

If you're working on a module and want it to integrate with the assessment flow:

1. **Include the integration script** in your module's HTML:

```html
<script src="../../modules-config.js"></script>
<script src="../../modules-integration.js"></script>
```

2. **Call completion handler** when the module is finished:

```javascript
// When module completes
if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
    const results = {
        score: 85,
        percentage: 85,
        status: 'completed'
        // Add your module-specific results
    };
    
    ModuleIntegration.handleModuleCompletion('listening', results);
} else {
    // Handle standalone completion (not from flow)
    // Your existing completion logic
}
```

3. **The integration script will automatically**:
   - Add a "Continue" button to your results page
   - Store results in localStorage/sessionStorage
   - Navigate back to the assessment flow

### Alternative: Manual Integration

If you prefer manual integration, you can:

```javascript
// Store results
sessionStorage.setItem('listeningCompleted', 'true');
localStorage.setItem('listeningResults', JSON.stringify(results));

// Navigate back
window.location.href = '../assessment-flow.html?listeningDone=true';
```

## Testing

1. **Test individual modules**:
   - Enable only one module
   - Go through the flow
   - Verify navigation works

2. **Test level flows**:
   - Test Basic level (listening + speaking)
   - Test Intermediate level (adds reading)
   - Test Advanced level (adds writing)

3. **Test module completion**:
   - Complete a module
   - Verify results are stored
   - Verify navigation to next module

## Common Issues

### Module not loading
- Check the URL in `modules-config.js`
- Verify the module is enabled (`enabled: true`)
- Check browser console for errors

### Results not showing
- Verify storage keys match in config
- Check that results are stored as JSON
- Verify `showCombinedResults()` function in `assessment-flow.html`

### Navigation issues
- Check that `fromAssessmentFlow` is set in sessionStorage
- Verify return URL in sessionStorage
- Check URL parameters match config

## Updating Module URLs

Simply update the URLs in `modules-config.js` - no other files need to be changed!

```javascript
// Change from localhost to production
baseUrl: 'https://your-production-server.com'

// Or update individual module
speaking: {
    url: 'https://speaking-module.example.com/index.html'
}
```

## Support

For questions or issues:
1. Check the browser console for errors
2. Verify configuration in `modules-config.js`
3. Test modules individually first
4. Check that all scripts are loaded correctly

