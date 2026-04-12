/**
 * Module Integration Utility
 * 
 * This script provides utilities for integrating modules into the assessment flow.
 * Include this script after modules-config.js
 */

(function() {
    'use strict';
    
    /**
     * Module Integration Manager
     */
    const ModuleIntegration = {
        /**
         * Initialize module integration
         */
        init: function() {
            console.log('Module Integration initialized');
        },
        
        /**
         * Navigate to a module
         * @param {string} moduleName - Name of the module
         * @param {object} options - Options for navigation
         */
        navigateToModule: function(moduleName, options = {}) {
            if (!isModuleEnabled(moduleName)) {
                alert(`${moduleName} module is not enabled. Please enable it in modules-config.js`);
                return;
            }
            
            // Store flow state
            sessionStorage.setItem('assessmentFlow', moduleName);
            sessionStorage.setItem('fromAssessmentFlow', 'true');
            
            // Store additional options if needed
            if (options.level) {
                sessionStorage.setItem('moduleLevel', options.level);
            }
            
            // Get module URL
            const url = getModuleUrl(moduleName, options);
            
            if (!url) {
                console.error(`Could not generate URL for module: ${moduleName}`);
                alert(`Error: Could not generate URL for ${moduleName} module`);
                return;
            }
            
            // Navigate to module
            window.location.href = url;
        },
        
        /**
         * Handle module completion and return to flow
         * @param {string} moduleName - Name of the completed module
         * @param {object} results - Results from the module
         */
        handleModuleCompletion: function(moduleName, results = null) {
            const moduleConfig = getModuleConfig(moduleName);
            
            if (!moduleConfig) {
                console.error(`Module ${moduleName} not found`);
                return;
            }
            
            // Store results
            if (results) {
                try {
                    localStorage.setItem(moduleConfig.storageKey, JSON.stringify(results));
                    sessionStorage.setItem(moduleConfig.storageKey, JSON.stringify(results));
                } catch (e) {
                    console.error('Failed to store results:', e);
                }
            }
            
            // Mark module as completed
            sessionStorage.setItem(moduleConfig.sessionKey, 'true');
            
            // Return to assessment flow
            const flowPath = sessionStorage.getItem('assessmentFlowPath') || 'assessment-flow.html';
            const paramName = MODULES_CONFIG.flow.paramNames[moduleName + 'Done'] || `${moduleName}Done`;
            
            const returnUrl = flowPath + (flowPath.includes('?') ? '&' : '?') + paramName + '=true';
            window.location.href = returnUrl;
        },
        
        /**
         * Check if coming from assessment flow
         * @returns {boolean} True if coming from flow
         */
        isFromFlow: function() {
            return sessionStorage.getItem('fromAssessmentFlow') === 'true';
        },
        
        /**
         * Get current flow state
         * @returns {string|null} Current module name or null
         */
        getFlowState: function() {
            return sessionStorage.getItem('assessmentFlow');
        },
        
        /**
         * Add continue button to module results page
         * @param {string} nextModuleName - Next module to navigate to (optional)
         * @param {string} buttonText - Custom button text (optional)
         */
        addContinueButton: function(nextModuleName = null, buttonText = null) {
            // Find results container
            const resultsContainer = document.getElementById('final-results-container') || 
                                   document.getElementById('results-container') ||
                                   document.querySelector('.results-container') ||
                                   document.querySelector('.completion-card') ||
                                   document.querySelector('.results') ||
                                   document.body;
            
            if (!resultsContainer) {
                console.warn('Could not find results container');
                return;
            }
            
            // Check if button already exists
            if (document.getElementById('flow-continue-btn')) {
                return;
            }
            
            // Determine button text and action
            const currentModule = this.getFlowState();
            const selectedLevel = sessionStorage.getItem('selectedLevel') || 'basic';
            const modules = getModulesForLevel(selectedLevel);
            const currentIndex = modules.indexOf(currentModule);
            
            let btnText = buttonText || 'Continue Assessment';
            let action = function() {
                window.location.href = '../assessment-flow.html';
            };
            
            if (nextModuleName) {
                btnText = buttonText || `Continue to ${getModuleConfig(nextModuleName)?.name || nextModuleName}`;
                action = function() {
                    ModuleIntegration.navigateToModule(nextModuleName);
                };
            } else if (currentIndex >= 0 && currentIndex < modules.length - 1) {
                const nextModule = modules[currentIndex + 1];
                const nextConfig = getModuleConfig(nextModule);
                btnText = buttonText || `Continue to ${nextConfig?.name || nextModule}`;
                action = function() {
                    window.location.href = '../assessment-flow.html';
                };
            } else {
                btnText = buttonText || 'View Combined Results';
                action = function() {
                    window.location.href = '../assessment-flow.html';
                };
            }
            
            // Create button
            const button = document.createElement('button');
            button.id = 'flow-continue-btn';
            button.textContent = btnText;
            button.className = 'flow-continue-button';
            button.style.cssText = `
                margin: 20px auto;
                padding: 14px 28px;
                background: #0a0a0a;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                font-size: 1rem;
                font-weight: 600;
                cursor: pointer;
                display: block;
                transition: all 0.3s ease;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            `;
            
            button.addEventListener('mouseenter', function() {
                this.style.background = '#1a1a1a';
                this.style.transform = 'translateY(-2px)';
                this.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            });
            
            button.addEventListener('mouseleave', function() {
                this.style.background = '#0a0a0a';
                this.style.transform = 'translateY(0)';
                this.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.1)';
            });
            
            button.onclick = action;
            
            // Insert button
            if (resultsContainer.appendChild) {
                resultsContainer.appendChild(button);
            } else {
                // If container doesn't support appendChild, try to find a better location
                const body = document.body;
                const firstChild = body.firstChild;
                if (firstChild) {
                    body.insertBefore(button, firstChild.nextSibling);
                } else {
                    body.appendChild(button);
                }
            }
        }
    };
    
    // Auto-detect and add continue button if coming from flow
    if (typeof document !== 'undefined') {
        document.addEventListener('DOMContentLoaded', function() {
            if (ModuleIntegration.isFromFlow()) {
                // Try to detect when results are shown
                const observer = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.addedNodes.length) {
                            // Small delay to ensure results are rendered
                            setTimeout(function() {
                                ModuleIntegration.addContinueButton();
                            }, 500);
                        }
                    });
                });
                
                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });
                
                // Also try after a short delay
                setTimeout(function() {
                    ModuleIntegration.addContinueButton();
                }, 1000);
            }
        });
    }
    
    // Make ModuleIntegration available globally
    if (typeof window !== 'undefined') {
        window.ModuleIntegration = ModuleIntegration;
    }
    
})();

