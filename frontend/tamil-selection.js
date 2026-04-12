// Assessment steps configuration
const assessmentSteps = {
    listening: {
        name: 'Listening Assessment',
        description: 'Listen to the audio carefully and understand the content. Only after understanding, you can answer the questions based on what you heard.',
        icon: '👂'
    },
    speaking: {
        name: 'Speaking Assessment',
        description: 'Read and understand the given prompts or questions. Only after understanding, you can speak and express your response clearly.',
        icon: '🗣️'
    },
    reading: {
        name: 'Reading Assessment',
        description: 'Read the text carefully and understand its meaning. Reading and understanding are different - make sure you comprehend the content before answering the questions.',
        icon: '📖'
    },
    writing: {
        name: 'Writing Assessment',
        description: 'Read and understand the given topic or question. Only after understanding, you can write and express your thoughts clearly in Tamil.',
        icon: '✍️'
    }
};

// Level configurations
const levelConfigs = {
    basic: ['listening', 'speaking'],
    intermediate: ['listening', 'speaking', 'reading'],
    advanced: ['listening', 'speaking', 'reading', 'writing']
};

// Step labels
const stepLabels = ['First', 'Second', 'Third', 'Fourth'];

// Generate personalized steps based on selected level
function generateSteps() {
    const selectedLevel = sessionStorage.getItem('selectedLevel') || 'basic';
    const steps = levelConfigs[selectedLevel] || levelConfigs.basic;
    const container = document.getElementById('sequence-steps');
    
    if (!container) return;
    
    // Clear container
    container.innerHTML = '';
    
    // Generate steps
    steps.forEach((stepKey, index) => {
        const step = assessmentSteps[stepKey];
        const stepNumber = index + 1;
        const stepLabel = stepLabels[index];
        
        // Create step element
        const stepElement = document.createElement('div');
        stepElement.className = `sequence-step step-${stepKey}`;
        stepElement.setAttribute('data-step', stepNumber);
        stepElement.style.animationDelay = `${index * 0.1}s`;
        
        stepElement.innerHTML = `
            <div class="step-icon-wrapper">
                <div class="step-number">${stepNumber}</div>
            </div>
            <div class="step-content">
                <h3>${step.name}</h3>
                <p>${step.description}</p>
                <div class="step-badge">${stepLabel} Step</div>
            </div>
        `;
        
        container.appendChild(stepElement);
        
        // Add arrow between steps (except after last step)
        if (index < steps.length - 1) {
            const arrow = document.createElement('div');
            arrow.className = 'sequence-arrow';
            arrow.textContent = '↓';
            container.appendChild(arrow);
        }
    });
    
    // Update intro text
    const introText = document.querySelector('.sequence-intro');
    if (introText) {
        const levelName = selectedLevel.charAt(0).toUpperCase() + selectedLevel.slice(1);
        introText.textContent = `Your ${levelName} Level Assessment will be conducted in the following order. For each step, you must first understand the content, then only proceed to answer or respond:`;
    }
}

// Check if level is selected, if not redirect to level selection
document.addEventListener('DOMContentLoaded', function() {
    const selectedLevel = sessionStorage.getItem('selectedLevel');
    
    if (!selectedLevel) {
        // Redirect to level selection if no level is selected
        window.location.href = 'level-selection.html';
        return;
    }
    
    // Generate personalized steps
    generateSteps();
});

