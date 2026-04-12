// Assessment Flow Integration Script
// This script should be included in speaking and reading test pages to integrate with the flow

(function() {
    'use strict';
    
    // Check if we came from assessment flow
    const fromFlow = sessionStorage.getItem('fromAssessmentFlow') === 'true';
    const flowState = sessionStorage.getItem('assessmentFlow');
    
    if (fromFlow) {
        // Store completion handler
        window.assessmentFlowComplete = function(results) {
            // Store results
            if (results) {
                try {
                    localStorage.setItem(flowState + 'Results', JSON.stringify(results));
                    sessionStorage.setItem(flowState + 'Results', JSON.stringify(results));
                } catch (e) {
                    console.error('Failed to store results:', e);
                }
            }
            
            // Mark as complete
            sessionStorage.setItem(flowState + 'Completed', 'true');
            
            // Add continue button to results page
            setTimeout(() => {
                addContinueButton();
            }, 1000);
        };
        
        function addContinueButton() {
            // Find results container or create button area
            const resultsContainer = document.getElementById('final-results-container') || 
                                   document.querySelector('.results-container') ||
                                   document.querySelector('.completion-card');
            
            if (resultsContainer) {
                // Check if button already exists
                if (document.getElementById('flow-continue-btn')) return;
                
                const button = document.createElement('button');
                button.id = 'flow-continue-btn';
                button.className = 'btn-primary';
                button.style.cssText = 'margin-top: 20px; width: 100%; max-width: 300px;';
                
                if (flowState === 'speaking') {
                    button.textContent = 'Continue to Reading Test';
                    button.onclick = function() {
                        window.location.href = '../assessment-flow.html';
                    };
                } else if (flowState === 'reading') {
                    button.textContent = 'View Combined Results';
                    button.onclick = function() {
                        window.location.href = '../../assessment-flow.html';
                    };
                }
                
                resultsContainer.appendChild(button);
            }
        }
        
        // Try to detect when results are shown
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.addedNodes.length) {
                    addContinueButton();
                }
            });
        });
        
        // Observe document for changes
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // Also try to hook into existing result functions
        const originalShowResults = window.showResultsPage;
        if (typeof originalShowResults === 'function') {
            window.showResultsPage = function() {
                originalShowResults.apply(this, arguments);
                setTimeout(addContinueButton, 500);
            };
        }
    }
})();

