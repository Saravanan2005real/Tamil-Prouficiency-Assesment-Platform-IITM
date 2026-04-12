/**
 * Example Integration Code for Module Pages
 * 
 * Copy this code to your module's HTML file to integrate with the assessment flow.
 * 
 * INSTRUCTIONS:
 * 1. Include the config and integration scripts in your HTML <head> or before closing </body>:
 *    <script src="../../modules-config.js"></script>
 *    <script src="../../modules-integration.js"></script>
 * 
 * 2. When your module completes, call the completion handler (see examples below)
 */

// Example 1: Simple completion handler
function handleModuleCompletion(results) {
    // Check if we came from the assessment flow
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        // Get the current module name (or set it explicitly)
        const moduleName = ModuleIntegration.getFlowState() || 'listening'; // Change to your module name
        
        // Prepare results object (customize based on your module)
        const moduleResults = {
            score: results.score || 0,
            percentage: results.percentage || 0,
            status: 'completed',
            // Add any other results your module provides
            ...results
        };
        
        // Handle completion - this will store results and navigate back to flow
        ModuleIntegration.handleModuleCompletion(moduleName, moduleResults);
    } else {
        // Handle standalone completion (not from assessment flow)
        // Your existing standalone completion logic here
        console.log('Module completed outside of assessment flow');
        showStandaloneResults(results);
    }
}

// Example 2: Integration with existing completion function
// If you already have a completion function, add this check:

/*
function showResults(results) {
    // Your existing results display logic
    displayResultsOnPage(results);
    
    // Add integration check at the end
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleName = 'listening'; // Change to your module name
        ModuleIntegration.handleModuleCompletion(moduleName, results);
    }
}
*/

// Example 3: Automatic continue button (optional)
// The integration script will automatically add a continue button,
// but if you want to customize it:

/*
window.addEventListener('DOMContentLoaded', function() {
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        // Wait for results to be displayed
        setTimeout(function() {
            // Customize button text or behavior
            ModuleIntegration.addContinueButton(null, 'Continue to Next Test');
        }, 1000);
    }
});
*/

// Example 4: Listening module with level parameter
function handleListeningCompletion(level, results) {
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleResults = {
            level: level,
            score: results.score || 0,
            percentage: results.percentage || 0,
            status: 'completed'
        };
        ModuleIntegration.handleModuleCompletion('listening', moduleResults);
    } else {
        // Standalone completion
        showStandaloneResults(results);
    }
}

// Example 5: Speaking module with detailed results
function handleSpeakingCompletion(results) {
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleResults = {
            avgOverall: results.avgOverall || 0,
            totalScore: results.totalScore || 0,
            questions: results.questions || [],
            status: 'completed'
        };
        ModuleIntegration.handleModuleCompletion('speaking', moduleResults);
    }
}

// Example 6: Reading module integration
function handleReadingCompletion(results) {
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleResults = {
            percentage: results.percentage || 0,
            marks: results.marks || 0,
            answers: results.answers || [],
            status: 'completed'
        };
        ModuleIntegration.handleModuleCompletion('reading', moduleResults);
    }
}

// Example 7: Writing module integration
function handleWritingCompletion(results) {
    if (window.ModuleIntegration && ModuleIntegration.isFromFlow()) {
        const moduleResults = {
            score: results.score || 0,
            percentage: results.percentage || 0,
            feedback: results.feedback || '',
            status: 'completed'
        };
        ModuleIntegration.handleModuleCompletion('writing', moduleResults);
    }
}

// Helper function for standalone completion (when not in flow)
function showStandaloneResults(results) {
    // Your existing logic for showing results when module is used standalone
    console.log('Standalone results:', results);
}

