// Tamil Reading Skill Assessment - Unified Interface
console.log("📜 Reading Skill Assessment loaded at", new Date().toISOString());

// Global state
let passages = [];
let currentLevel = 1; // 1 = basic, 2 = intermediate, 3 = advanced
let timerInterval = null;
let timeRemaining = 30 * 60; // 30 minutes in seconds
let allAnswers = {}; // Store all answers: { 'basic-1': 'answer', 'intermediate-2': 'answer', ... }
let tamilKeyboards = {};
// Assessment flow: level from URL (e.g. ?level=advanced) – only advanced gets "Continue with Writing"
let flowLevel = '';

// Level mapping
const levelMap = {
    1: 'basic',
    2: 'intermediate',
    3: 'advanced'
};

// DOM elements
const el = {
    timer: document.getElementById('global-timer'),
    levelBtns: document.querySelectorAll('.level-btn'),
    passageBox: document.getElementById('passage-box'),
    questionsContainer: document.getElementById('questions-container'),
    nextBtn: document.getElementById('next-btn'),
    submitBtn: document.getElementById('submit-btn'),
    resultCard: document.getElementById('result-card'),
    resultSummary: document.getElementById('result-summary'),
    resultDetails: document.getElementById('result-details')
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    console.log("🚀 Initializing Reading Skill Assessment...");

    // On load/refresh: clear reading answers and timer so user gets a fresh assessment
    localStorage.removeItem('readingAnswers');
    localStorage.removeItem('readingTimerStart');
    allAnswers = {};

    // Get level from URL for flow (advanced = show "Continue with Writing" after reading)
    var params = new URLSearchParams(window.location.search);
    flowLevel = (params.get('level') || '').toLowerCase();

    // Check if Tamil keyboard is loaded
    if (window.TamilKeyboard) {
        console.log("✅ Tamil Keyboard is available");
    } else {
        console.warn("⚠️ Tamil Keyboard not loaded yet - will check again after delay");
        setTimeout(() => {
            if (window.TamilKeyboard) {
                console.log("✅ Tamil Keyboard loaded after delay");
            } else {
                console.error("❌ Tamil Keyboard still not available");
            }
        }, 1000);
    }

    // Load saved answers from localStorage (will be empty after clear above)
    loadAnswers();

    // Load passages
    await loadPassages();

    // Initialize timer
    initTimer();

    // Setup level buttons
    setupLevelButtons();

    // Load current level
    loadLevel(currentLevel);

    console.log("✅ Initialization complete!");
});

// Load all passages from API
async function loadPassages() {
    try {
        const response = await fetch('/api/paragraphs');
        const data = await response.json();
        passages = data.passages || [];
        console.log(`✅ Loaded ${passages.length} passages`);
    } catch (error) {
        console.error('❌ Error loading passages:', error);
        el.passageBox.innerHTML = '<p style="color: #c0392b;">Error loading passages. Please refresh the page.</p>';
    }
}

// Initialize 30-minute timer
function initTimer() {
    // Check if timer was already started
    const savedTime = localStorage.getItem('readingTimerStart');
    if (savedTime) {
        const elapsed = Math.floor((Date.now() - parseInt(savedTime)) / 1000);
        timeRemaining = Math.max(0, 30 * 60 - elapsed);
    } else {
        localStorage.setItem('readingTimerStart', Date.now().toString());
    }

    updateTimerDisplay();
    timerInterval = setInterval(() => {
        if (timeRemaining > 0) {
            timeRemaining--;
            updateTimerDisplay();
        } else {
            clearInterval(timerInterval);
            handleTimeExpired();
        }
    }, 1000);
}

// Update timer display
function updateTimerDisplay() {
    if (!el.timer) return;

    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    const timeString = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    el.timer.textContent = timeString;

    // Add warning class when less than 5 minutes
    if (timeRemaining < 5 * 60 && timeRemaining > 0) {
        el.timer.classList.add('warning');
    } else if (timeRemaining === 0) {
        el.timer.classList.add('expired');
    } else {
        el.timer.classList.remove('warning', 'expired');
    }
}

// Handle time expired
function handleTimeExpired() {
    alert('Time is up! Your answers will be automatically submitted.');
    submitAllAnswers();
}

// Setup level navigation buttons
function setupLevelButtons() {
    el.levelBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const level = parseInt(btn.dataset.level);
            switchLevel(level);
        });
    });
}

// Switch to a different level
function switchLevel(level) {
    if (level < 1 || level > 3) return;

    // Save current answers before switching
    saveCurrentAnswers();

    // Update active button
    el.levelBtns.forEach(btn => {
        btn.classList.toggle('active', parseInt(btn.dataset.level) === level);
    });

    currentLevel = level;
    loadLevel(level);
}

// Load a specific level
function loadLevel(level) {
    const passageId = levelMap[level];
    const passage = passages.find(p => p.id === passageId);

    if (!passage) {
        console.error(`❌ Passage not found for level ${level}`);
        return;
    }

    // Render passage
    renderPassage(passage);

    // Render questions
    renderQuestions(passage);

    // Show/hide buttons
    if (level < 3) {
        el.nextBtn.style.display = 'block';
        el.submitBtn.style.display = 'none';
    } else {
        el.nextBtn.style.display = 'none';
        el.submitBtn.style.display = 'block';
    }

    // Setup button handlers
    el.nextBtn.onclick = () => {
        saveCurrentAnswers();
        switchLevel(level + 1);
    };

    el.submitBtn.onclick = () => {
        saveCurrentAnswers();
        submitAllAnswers();
    };
}

// Render passage
function renderPassage(passage) {
    if (!el.passageBox) return;

    const html = `
        <div class="paragraph-box">
            <div class="paragraph-text">${passage.paragraph.tamil || ''}</div>
        </div>
    `;

    el.passageBox.innerHTML = html;
}

// Render questions for current level
function renderQuestions(passage) {
    if (!el.questionsContainer) return;

    const questions = passage.questions || {};
    const passageId = passage.id;

    el.questionsContainer.innerHTML = '';

    // Sort questions by number
    const questionNumbers = Object.keys(questions).map(Number).sort((a, b) => a - b);

    questionNumbers.forEach(qNum => {
        const question = questions[qNum];
        const answerKey = `${passageId}-${qNum}`;
        const savedAnswer = allAnswers[answerKey] || '';

        const questionDiv = document.createElement('div');
        questionDiv.className = 'question';
        questionDiv.dataset.questionId = qNum;
        questionDiv.dataset.passageId = passageId;

        const label = document.createElement('label');
        label.innerHTML = `
            Q${qNum}. <strong>${question.text_tamil || ''}</strong>
            <span style="color: #666; font-weight: 600; font-size: 0.9em; margin-left: 8px;">[${question.marks || 1} mark${question.marks > 1 ? 's' : ''}]</span>
            ${question.text_english ? `<div style="color: #6c757d; font-size: 0.9em; font-style: italic; margin-top: 6px; padding-left: 0; line-height: 1.4;">${question.text_english}</div>` : ''}
        `;
        questionDiv.appendChild(label);

        const textarea = document.createElement('textarea');
        textarea.id = `answer-${answerKey}`;
        textarea.name = `answer-${answerKey}`;
        textarea.placeholder = 'Type your answer in Tamil here...';
        textarea.value = savedAnswer;
        textarea.setAttribute('data-passage-id', passageId);
        textarea.setAttribute('data-question-num', qNum);

        // Auto-save on input
        textarea.addEventListener('input', () => {
            allAnswers[answerKey] = textarea.value;
            saveAnswers();
        });

        // Auto-show Tamil keyboard on focus (like listening module)
        textarea.addEventListener('focus', (e) => {
            console.log('📝 Textarea focused:', textarea.id);
            if (window.TamilKeyboard && window.TamilKeyboard.show) {
                console.log('⌨️ Calling TamilKeyboard.show()');
                window.TamilKeyboard.show(textarea);
            } else {
                console.error('❌ TamilKeyboard not available');
            }
        });

        questionDiv.appendChild(textarea);

        el.questionsContainer.appendChild(questionDiv);
    });
}

// Tamil keyboard is now auto-shown on focus, no toggle function needed

// Save current answers to localStorage
function saveCurrentAnswers() {
    // Answers are already saved on input, but we'll ensure they're persisted
    saveAnswers();
}

// Save all answers to localStorage
function saveAnswers() {
    try {
        localStorage.setItem('readingAnswers', JSON.stringify(allAnswers));
    } catch (e) {
        console.error('Error saving answers:', e);
    }
}

// Load answers from localStorage
function loadAnswers() {
    try {
        const saved = localStorage.getItem('readingAnswers');
        if (saved) {
            allAnswers = JSON.parse(saved);
            console.log(`✅ Loaded ${Object.keys(allAnswers).length} saved answers`);
        }
    } catch (e) {
        console.error('Error loading answers:', e);
        allAnswers = {};
    }
}

// Submit all answers and evaluate
async function submitAllAnswers() {
    // Clear timer
    if (timerInterval) {
        clearInterval(timerInterval);
    }

    // Disable buttons
    el.nextBtn.disabled = true;
    el.submitBtn.disabled = true;

    // Show loading
    el.resultCard.style.display = 'block';
    el.resultSummary.innerHTML = '<div class="loading"><div class="spinner"></div><p>Evaluating all answers...</p></div>';
    el.resultDetails.innerHTML = '';

    try {
        // Evaluate all 15 questions
        const results = await evaluateAllQuestions();

        // Display results
        displayResults(results);

    } catch (error) {
        console.error('Error evaluating answers:', error);
        el.resultSummary.innerHTML = '<p style="color: #c0392b;">Error evaluating answers. Please try again.</p>';
    }
}

// Evaluate all 15 questions in parallel for speed
async function evaluateAllQuestions() {
    const results = {
        basic: { marks: 0, maxMarks: 0, questions: [] },
        intermediate: { marks: 0, maxMarks: 0, questions: [] },
        advanced: { marks: 0, maxMarks: 0, questions: [] }
    };

    const evalPromises = [];

    // Collect all evaluation tasks
    for (const passage of passages) {
        const passageId = passage.id;
        const questions = passage.questions || {};
        const questionNumbers = Object.keys(questions).map(Number).sort((a, b) => a - b);

        for (const qNum of questionNumbers) {
            const answerKey = `${passageId}-${qNum}`;
            const userAnswer = allAnswers[answerKey] || '';
            const question = questions[qNum];
            const maxMarks = question.marks || 1;

            results[passageId].maxMarks += maxMarks;

            if (!userAnswer.trim()) {
                results[passageId].questions.push({
                    number: qNum,
                    marks: 0,
                    maxMarks: maxMarks,
                    passed: false
                });
                continue;
            }

            // Push promise to array
            evalPromises.push((async () => {
                try {
                    const evalResponse = await fetch('/api/evaluate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            questionNumber: qNum,
                            paragraphId: passageId,
                            userAnswer: userAnswer
                        })
                    });

                    const evalData = await evalResponse.json();
                    return { passageId, qNum, maxMarks, evalData, userAnswer };
                } catch (error) {
                    return { passageId, qNum, maxMarks, error: 'Evaluation error', userAnswer };
                }
            })());
        }
    }

    // Wait for all evaluations to complete
    const evaluations = await Promise.all(evalPromises);

    // Process results
    evaluations.forEach(ev => {
        const { passageId, qNum, maxMarks, evalData, error, userAnswer } = ev;
        if (error) {
            results[passageId].questions.push({
                number: qNum, marks: 0, maxMarks, passed: false, answer: userAnswer, error
            });
        } else if (evalData.success) {
            const marks = evalData.marks || 0;
            results[passageId].marks += marks;
            results[passageId].questions.push({
                number: qNum,
                marks,
                maxMarks,
                passed: evalData.passed || false,
                answer: userAnswer,
                question_text: evalData.question_text,
                expected_answers: evalData.expected_answers
            });
        } else {
            results[passageId].questions.push({
                number: qNum, marks: 0, maxMarks, passed: false, answer: userAnswer, error: evalData.error
            });
        }
    });

    return results;
}

// Display results
function displayResults(results) {
    // Calculate totals
    const totalMarks = results.basic.marks + results.intermediate.marks + results.advanced.marks;
    const totalMaxMarks = results.basic.maxMarks + results.intermediate.maxMarks + results.advanced.maxMarks;
    const percentage = totalMaxMarks > 0 ? ((totalMarks / totalMaxMarks) * 100).toFixed(1) : '0.0';

    // Summary
    el.resultSummary.innerHTML = `
        <div style="text-align: center; margin-bottom: 32px;">
            <h3 style="font-size: 2rem; font-weight: 700; color: #000; margin-bottom: 16px;">
                Overall Score: ${totalMarks}/${totalMaxMarks}
            </h3>
            <div style="font-size: 1.5rem; font-weight: 600; color: #666; margin-bottom: 8px;">
                Percentage: ${percentage}%
            </div>
            <div style="font-size: 1.2rem; font-weight: 600; color: ${parseFloat(percentage) >= 40 ? '#28a745' : '#dc3545'};">
                ${parseFloat(percentage) >= 40 ? '✓ Passed' : '✗ Failed'}
            </div>
        </div>
    `;

    // Save for Teacher Agent
    localStorage.setItem('readingResults', JSON.stringify(results));

    // Show AI Teacher Section
    const aiSection = document.getElementById('aiTeacherSection');
    if (aiSection) {
        aiSection.style.display = 'block';
        generateTeacherAnalysis();
    }

    // Per-level details
    const levelNames = {
        basic: 'Level 1 (Basic)',
        intermediate: 'Level 2 (Intermediate)',
        advanced: 'Level 3 (Advanced)'
    };

    let detailsHtml = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin-top: 24px;">';

    for (const [passageId, result] of Object.entries(results)) {
        const levelPercentage = result.maxMarks > 0 ? ((result.marks / result.maxMarks) * 100).toFixed(1) : '0.0';

        detailsHtml += `
            <div style="background: #fafafa; border-radius: 12px; padding: 20px; border: 1px solid rgba(0, 0, 0, 0.08);">
                <h4 style="font-size: 1.2rem; font-weight: 700; color: #000; margin-bottom: 12px;">
                    ${levelNames[passageId] || passageId}
                </h4>
                <div style="font-size: 1.5rem; font-weight: 700; color: #000; margin-bottom: 8px;">
                    ${result.marks}/${result.maxMarks}
                </div>
                <div style="font-size: 1rem; color: #666; margin-bottom: 16px;">
                    ${levelPercentage}%
                </div>
                <div style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(0, 0, 0, 0.08);">
                    <div style="font-size: 0.9rem; color: #666; margin-bottom: 8px;">Question-wise:</div>
                    ${result.questions.map(q => `
                        <div style="font-size: 0.85rem; color: #1a1a1a; margin-bottom: 4px;">
                            Q${q.number}: ${q.marks}/${q.maxMarks} ${q.passed ? '✓' : '✗'}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    detailsHtml += '</div>';

    // Only for advanced level: show "Continue with Writing Assessment" button
    if (flowLevel === 'advanced') {
        detailsHtml += '<div style="margin-top: 28px; padding-top: 24px; border-top: 1px solid rgba(0,0,0,0.08);">';
        detailsHtml += '<a href="continue-writing.html" class="btn-primary" style="display: inline-block; padding: 14px 28px; text-decoration: none; color: #fff; background: #0a0a0a; border-radius: 8px; font-weight: 600;">Continue with Writing Assessment</a>';
        detailsHtml += '</div>';
    }

    el.resultDetails.innerHTML = detailsHtml;

    // Scroll to results
    el.resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function generateTeacherAnalysis() {
    const container = document.getElementById('aiReportContainer');
    if (container && window.teacherAgent) {
        try {
            const reportMarkdown = await window.teacherAgent.generateReport();
            if (typeof marked === 'undefined') {
                container.innerHTML = `<div class="ai-report-card"><div class="ai-report-content">${reportMarkdown}</div></div>`;
                return;
            }
            const renderedHTML = marked.parse(reportMarkdown);
            container.innerHTML = `
                <div class="ai-report-card">
                    <div class="ai-report-content">
                        ${renderedHTML}
                    </div>
                    <div style="margin-top: 30px; text-align: center;">
                        <button onclick="window.teacherAgent.downloadPDF(\`${reportMarkdown.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)" 
                                class="btn-primary" 
                                style="background: #198754; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; gap: 8px;">
                            <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                            Download PDF Report
                        </button>
                    </div>
                </div>
            `;
        } catch (error) {
            console.error('Teacher Analysis Error:', error);
            container.innerHTML = `
                <div class="ai-report-card" style="border-color: #dc3545;">
                    <p style="color: #dc3545;"><strong>Teacher Service Unavailable:</strong> ${error.message}</p>
                    <p style="font-size: 0.9em; margin-top: 10px;">Please check your internet connection or the Groq API key.</p>
                </div>
            `;
        }
    }
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    saveCurrentAnswers();
});
