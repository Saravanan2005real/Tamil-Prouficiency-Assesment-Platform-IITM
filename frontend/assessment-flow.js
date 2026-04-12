// Assessment Flow Integration Script
// This script should be included in all test pages to integrate with the flow
/**
 * HOW TO USE:
 * 1. Include this script in your module's index.html or results page.
 * 2. When the test finishes, call window.assessmentFlowComplete(results);
 */

(function () {
    'use strict';

    // Config: Portal URL is usually port 5000
    const PORTAL_BASE_URL = 'http://127.0.0.1:5000';

    // Check if we came from assessment flow
    // Modules might set this in sessionStorage when they are launched from the flow
    const fromFlow = sessionStorage.getItem('fromAssessmentFlow') === 'true' ||
        new URLSearchParams(window.location.search).get('fromFlow') === '1';

    // Determine which module we are in
    let currentModule = '';
    const path = window.location.pathname.toLowerCase();
    if (path.includes('listening')) currentModule = 'listening';
    else if (path.includes('speaking') || window.location.port === '8001') currentModule = 'speaking';
    else if (path.includes('reading') || window.location.port === '5003') currentModule = 'reading';
    else if (path.includes('writing') || window.location.port === '5002') currentModule = 'writing';

    if (fromFlow) {
        console.log(`🚀 Assessment Flow detected in ${currentModule} module`);
        sessionStorage.setItem('fromAssessmentFlow', 'true');

        // Store results handler
        window.assessmentFlowComplete = function (results) {
            console.log(`✅ ${currentModule} Assessment Complete!`);

            // Store results to localStorage for the Teacher Agent
            if (results && currentModule) {
                try {
                    localStorage.setItem(currentModule + 'Results', JSON.stringify(results));
                    sessionStorage.setItem(currentModule + 'Results', JSON.stringify(results));
                } catch (e) {
                    console.error('Failed to store results:', e);
                }
            }

            // Mark as complete in session
            if (currentModule) {
                sessionStorage.setItem(currentModule + 'Completed', 'true');
            }

            // Add the "Continue" button to UI
            setTimeout(() => {
                addFlowContinueButton();
            }, 500);
        };

        function addFlowContinueButton() {
            // Find container
            const resultsContainer = document.getElementById('final-results-container') ||
                document.getElementById('results-section') ||
                document.querySelector('.results-container') ||
                document.querySelector('.completion-card') ||
                document.getElementById('result-card');

            if (resultsContainer) {
                if (document.getElementById('flow-continue-btn')) return;

                const btnArea = document.createElement('div');
                btnArea.style.cssText = 'margin-top: 30px; padding: 20px; border-top: 2px solid #eee; text-align: center; width: 100%;';

                const button = document.createElement('button');
                button.id = 'flow-continue-btn';
                button.className = 'btn-primary'; // Use module's own class if possible

                // Styling for consistency if no class exists
                button.style.cssText = 'padding: 15px 40px; background: #0a0a0a; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; font-size: 1.1rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1);';

                let nextAction = '';
                if (currentModule === 'listening') nextAction = 'speakingDone=true';
                else if (currentModule === 'speaking') nextAction = 'speakingDone=true';
                else if (currentModule === 'reading') nextAction = 'readingDone=true';
                else if (currentModule === 'writing') nextAction = 'writingDone=true';

                button.textContent = 'Continue Assessment Flow →';
                if (currentModule === 'writing') button.textContent = 'View Final Results →';

                button.onclick = function () {
                    const nextUrl = `${PORTAL_BASE_URL}/assessment-flow.html?${nextAction}`;
                    window.location.href = nextUrl;
                };

                btnArea.appendChild(button);
                resultsContainer.appendChild(btnArea);
                console.log('🔘 Added Flow Continue Button');
            }
        }

        // Auto-detect completion UI if possible
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.addedNodes.length) {
                    // Check if results were just shown
                    const res = document.getElementById('final-results-container') || document.getElementById('result-card');
                    if (res) addFlowContinueButton();
                }
            });
        });

        observer.observe(document.body, { childList: true, subtree: true });
    }
})();
