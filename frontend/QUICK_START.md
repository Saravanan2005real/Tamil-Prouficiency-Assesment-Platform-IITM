# Quick Start Guide - Module Integration

This guide will help you quickly integrate your 4 modules (Listening, Speaking, Reading, Writing) into the unified assessment platform.

## What Was Created

1. **`modules-config.js`** - Central configuration for all modules
2. **`modules-integration.js`** - Integration utilities
3. **`assessment-flow.html`** - Updated to use the configuration system
4. **Documentation files** - Guides for integration

## Quick Setup (5 Minutes)

### Step 1: Configure Module URLs

Open `modules-config.js` and update the URLs for your modules:

```javascript
// If all modules are on the same server (e.g., localhost:5000)
baseUrl: 'http://localhost:5000'

// OR if modules are on different servers, set individual URLs:
modules: {
    listening: {
        url: 'http://localhost:5000/listening/index.html',
        // ...
    },
    speaking: {
        url: 'http://localhost:3000/speaking/index.html',
        // ...
    }
}
```

### Step 2: Enable Modules

In `modules-config.js`, make sure modules are enabled:

```javascript
listening: {
    enabled: true,  // ✓ Enable when ready
    // ...
},
speaking: {
    enabled: true,  // ✓ Enable when ready
    // ...
},
reading: {
    enabled: true,  // ✓ Enable when ready
    // ...
},
writing: {
    enabled: false, // Set to true when writing module is ready
    // ...
}
```

### Step 3: Test the Flow

1. Open `index.html` in your browser
2. Click "Start Assessment"
3. Select a level (Basic/Intermediate/Advanced)
4. The system will guide you through enabled modules

## Integrating Your Module Pages

### For each module (listening, speaking, reading, writing):

1. **Include the scripts** in your module's HTML file:

```html
<!-- Add before closing </body> tag -->
<script src="../../modules-config.js"></script>
<script src="../../modules-integration.js"></script>
```

2. **Update your completion handler**:

```javascript
// When your module completes, add this check:
function handleCompletion(results) {
    // Your existing result display logic
    showResults(results);
    
    // Add integration check
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleName = 'listening'; // Change to your module name
        ModuleIntegration.handleModuleCompletion(moduleName, results);
    }
}
```

See `module-integration-example.js` for detailed examples.

## Module URLs - Current Setup

Based on your code, the current URLs are:
- **Listening**: `http://localhost:5000/listening/index.html?level=1`
- **Speaking**: `http://localhost:5000/speaking/index.html`
- **Reading**: `http://localhost:5000/reading/index.html`
- **Writing**: Not yet configured (set `enabled: true` when ready)

## Testing Checklist

- [ ] All module URLs are correct in `modules-config.js`
- [ ] Modules are enabled in config
- [ ] Test Basic level (listening + speaking)
- [ ] Test Intermediate level (adds reading)
- [ ] Test Advanced level (adds writing when enabled)
- [ ] Verify results are stored correctly
- [ ] Verify navigation between modules works

## Common Configurations

### All modules on same server
```javascript
baseUrl: 'http://localhost:5000'
// Leave url: '' empty in each module config
```

### Different servers for each module
```javascript
baseUrl: ''  // Leave empty

modules: {
    listening: { url: 'http://server1.com/listening/' },
    speaking: { url: 'http://server2.com/speaking/' },
    // ...
}
```

### Production URLs
```javascript
baseUrl: 'https://your-production-domain.com'
// Or set individual URLs
```

## Need Help?

- See `MODULES_INTEGRATION_GUIDE.md` for detailed documentation
- Check `module-integration-example.js` for code examples
- Check browser console for errors
- Verify module URLs are accessible

## Next Steps

1. ✅ Configure URLs in `modules-config.js`
2. ✅ Enable modules you want to test
3. ✅ Add integration code to your module pages
4. ✅ Test the complete flow
5. ✅ Enable writing module when ready

