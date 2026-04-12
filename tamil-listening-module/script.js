// Minimal frontend: audio + questions + answers
console.log("📜 script.js loaded at", new Date().toISOString());

// Speech-to-text functionality using Whisper
// Note: Microphone is available in the keyboard, not in individual answer boxes
// This function is kept for reference but not used (mic is in keyboard only)

/**
 * Add microphone button to a textarea for speech-to-text
 * NOTE: This function is NOT used - microphone is only in the keyboard
 * @deprecated - Use keyboard mic instead
 */
function addMicrophoneButton(textarea, container) {
  // This function is intentionally empty - mic buttons are removed from answer boxes
  // Microphone is only available in the Tamil keyboard
  return;
  // Create microphone button container
  const micContainer = document.createElement("div");
  micContainer.style.cssText = `
    position: absolute;
    right: 12px;
    bottom: 12px;
    z-index: 10;
  `;

  const micButton = document.createElement("button");
  micButton.type = "button";
  micButton.className = "mic-button";
  micButton.innerHTML = "🎤";
  micButton.title = "பேசி பதிலளிக்க (Click to speak)";
  micButton.style.cssText = `
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 2px solid #667eea;
    background: #ffffff;
    color: #667eea;
    font-size: 18px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s ease;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.2);
  `;

  // Store state for this specific button
  const state = {
    isRecording: false,
    mediaRecorder: null,
    audioChunks: [],
    stream: null,
    placeholderInterval: null,
    recordingStartTime: null,
    recordingIndicator: null
  };
  recordingState.set(textarea.id, state);

  // Add visual recording indicator (red pulsing dot)
  const recordingIndicator = document.createElement("div");
  recordingIndicator.className = "recording-indicator";
  recordingIndicator.style.cssText = `
    position: absolute;
    top: 12px;
    right: 12px;
    width: 12px;
    height: 12px;
    background: #dc3545;
    border-radius: 50%;
    display: none;
    animation: pulse 1.5s ease-in-out infinite;
    z-index: 11;
  `;

  // Add pulse animation
  if (!document.getElementById('recording-pulse-style')) {
    const style = document.createElement('style');
    style.id = 'recording-pulse-style';
    style.textContent = `
      @keyframes pulse {
        0%, 100% {
          opacity: 1;
          transform: scale(1);
        }
        50% {
          opacity: 0.5;
          transform: scale(1.2);
        }
      }
    `;
    document.head.appendChild(style);
  }

  container.appendChild(recordingIndicator);
  state.recordingIndicator = recordingIndicator;

  // Hover effect
  micButton.addEventListener("mouseenter", () => {
    if (!state.isRecording) {
      micButton.style.background = "#667eea";
      micButton.style.color = "#ffffff";
      micButton.style.transform = "scale(1.1)";
    }
  });

  micButton.addEventListener("mouseleave", () => {
    if (!state.isRecording) {
      micButton.style.background = "#ffffff";
      micButton.style.color = "#667eea";
      micButton.style.transform = "scale(1)";
    }
  });

  // Recording state
  const updateMicButton = (recording) => {
    state.isRecording = recording;
    if (recording) {
      micButton.innerHTML = "🔴";
      micButton.style.background = "#dc3545";
      micButton.style.borderColor = "#dc3545";
      micButton.style.color = "#ffffff";
      micButton.title = "பதிவு நிறுத்த (Click to stop)";
      // Show recording indicator
      if (state.recordingIndicator) {
        state.recordingIndicator.style.display = "block";
      }
    } else {
      micButton.innerHTML = "🎤";
      micButton.style.background = "#ffffff";
      micButton.style.borderColor = "#667eea";
      micButton.style.color = "#667eea";
      micButton.title = "பேசி பதிலளிக்க (Click to speak)";
      // Hide recording indicator
      if (state.recordingIndicator) {
        state.recordingIndicator.style.display = "none";
      }
    }
  };

  // Click handler
  micButton.addEventListener("click", async () => {
    if (state.isRecording) {
      // Stop recording
      stopRecording(textarea, updateMicButton, state);
    } else {
      // Start recording
      await startRecording(textarea, updateMicButton, state);
    }
  });

  micContainer.appendChild(micButton);
  container.appendChild(micContainer);
}

/**
 * Start audio recording
 */
async function startRecording(textarea, updateMicButton, state) {
  try {
    console.log("🎤 Starting recording for textarea:", textarea.id);

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 16000,
        channelCount: 1
      }
    });

    state.stream = stream;

    // Check if stream is active
    const audioTracks = stream.getAudioTracks();
    console.log("🎤 Audio tracks:", audioTracks.length);
    if (audioTracks.length > 0) {
      console.log("🎤 Track settings:", audioTracks[0].getSettings());
      console.log("🎤 Track state:", audioTracks[0].readyState);
    }

    // Try different MIME types for better compatibility
    let mimeType = 'audio/webm;codecs=opus';
    if (!MediaRecorder.isTypeSupported(mimeType)) {
      mimeType = 'audio/webm';
      if (!MediaRecorder.isTypeSupported(mimeType)) {
        mimeType = 'audio/mp4';
        if (!MediaRecorder.isTypeSupported(mimeType)) {
          mimeType = ''; // Use browser default
        }
      }
    }

    console.log("🎤 Using MIME type:", mimeType || "browser default");

    const options = mimeType ? { mimeType: mimeType } : {};
    state.mediaRecorder = new MediaRecorder(stream, options);

    state.audioChunks = [];
    state.recordingStartTime = Date.now();

    // Show recording indicator in textarea
    const originalPlaceholder = textarea.placeholder;
    textarea.placeholder = "🔴 பதிவு செய்யப்படுகிறது... பேசுங்கள் / Recording... Speak now";

    // Update placeholder periodically to show recording is active
    state.placeholderInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - state.recordingStartTime) / 1000);
      textarea.placeholder = `🔴 பதிவு செய்யப்படுகிறது... ${elapsed}வி / Recording... ${elapsed}s`;
    }, 1000);

    state.mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        state.audioChunks.push(event.data);
        console.log("📦 Audio chunk received:", event.data.size, "bytes, total chunks:", state.audioChunks.length);
      } else {
        console.warn("⚠️ Empty data chunk received");
      }
    };

    state.mediaRecorder.onstart = () => {
      console.log("✅ MediaRecorder started, state:", state.mediaRecorder.state);
    };

    state.mediaRecorder.onstop = async () => {
      console.log("🛑 Recording stopped, processing audio...");
      console.log("📦 Total chunks collected:", state.audioChunks.length);

      // Clear placeholder interval
      if (state.placeholderInterval) {
        clearInterval(state.placeholderInterval);
        state.placeholderInterval = null;
      }

      if (state.audioChunks.length === 0) {
        console.error("❌ No audio chunks collected!");
        textarea.placeholder = originalPlaceholder;
        alert("பதிவு தரவு கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும்.\n\nNo recording data collected. Please try again.");
        updateMicButton(false);
        if (state.stream) {
          state.stream.getTracks().forEach(track => track.stop());
          state.stream = null;
        }
        return;
      }

      const audioBlob = new Blob(state.audioChunks, { type: mimeType || 'audio/webm' });
      console.log("📦 Audio blob created:", audioBlob.size, "bytes, type:", audioBlob.type);

      if (audioBlob.size < 1000) {
        console.error("❌ Audio blob too small:", audioBlob.size, "bytes");
        textarea.placeholder = originalPlaceholder;
        alert("பதிவு மிகவும் குறுகியது. நீண்ட நேரம் பேசுங்கள்.\n\nRecording too short. Please speak longer.");
        updateMicButton(false);
        if (state.stream) {
          state.stream.getTracks().forEach(track => track.stop());
          state.stream = null;
        }
        return;
      }

      // Microphone functionality removed - no longer processing audio
      console.log("⚠️ Microphone functionality has been removed");

      // Stop all tracks
      if (state.stream) {
        state.stream.getTracks().forEach(track => track.stop());
        state.stream = null;
      }
    };

    state.mediaRecorder.onerror = (event) => {
      console.error("❌ MediaRecorder error:", event.error);
      if (state.placeholderInterval) {
        clearInterval(state.placeholderInterval);
        state.placeholderInterval = null;
      }
      textarea.placeholder = originalPlaceholder;
      updateMicButton(false);
      alert("பதிவு பிழை. மீண்டும் முயற்சிக்கவும்.\n\nRecording error. Please try again.");
    };

    // Start recording with timeslice to ensure data collection
    // timeslice: collect data every 1000ms (1 second)
    state.mediaRecorder.start(1000);
    updateMicButton(true);

    // Verify recording started
    setTimeout(() => {
      if (state.mediaRecorder && state.mediaRecorder.state === 'recording') {
        console.log("✅ Recording confirmed active, state:", state.mediaRecorder.state);
      } else {
        console.error("❌ Recording not active! State:", state.mediaRecorder?.state);
        updateMicButton(false);
        if (state.placeholderInterval) {
          clearInterval(state.placeholderInterval);
          state.placeholderInterval = null;
        }
        textarea.placeholder = originalPlaceholder;
        alert("பதிவு தொடங்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.\n\nCould not start recording. Please try again.");
      }
    }, 100);

  } catch (error) {
    console.error("❌ Error starting recording:", error);
    updateMicButton(false);
    let errorMsg = "மைக்ரோஃபோன் அனுமதி தேவை. தயவுசெய்து மைக்ரோஃபோன் அனுமதியை வழங்கவும்.\n\nMicrophone permission required. Please allow microphone access.";
    if (error.name === 'NotAllowedError') {
      errorMsg = "மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது. தயவுசெய்து உலாவி அமைப்புகளில் அனுமதியை வழங்கவும்.\n\nMicrophone permission denied. Please allow microphone access in browser settings.";
    } else if (error.name === 'NotFoundError') {
      errorMsg = "மைக்ரோஃபோன் கிடைக்கவில்லை.\n\nMicrophone not found.";
    }
    alert(errorMsg);
  }
}

/**
 * Stop audio recording
 */
function stopRecording(textarea, updateMicButton, state) {
  console.log("🛑 Stop recording requested, current state:", state.mediaRecorder?.state);

  if (state.mediaRecorder) {
    if (state.mediaRecorder.state === 'recording') {
      console.log("🛑 Stopping active recording...");
      state.mediaRecorder.stop();
      updateMicButton(false);
      console.log("✅ Stop command sent");
    } else if (state.mediaRecorder.state === 'paused') {
      console.log("🛑 Resuming and stopping paused recording...");
      state.mediaRecorder.resume();
      state.mediaRecorder.stop();
      updateMicButton(false);
    } else {
      console.warn("⚠️ Recording not in active state:", state.mediaRecorder.state);
      updateMicButton(false);
      // Force cleanup
      if (state.stream) {
        state.stream.getTracks().forEach(track => track.stop());
        state.stream = null;
      }
      if (state.placeholderInterval) {
        clearInterval(state.placeholderInterval);
        state.placeholderInterval = null;
      }
    }
  } else {
    console.warn("⚠️ No MediaRecorder instance found");
    updateMicButton(false);
  }
}

/**
 * Send audio to Whisper API for transcription
 * NOTE: This function has been removed - microphone functionality is no longer available
 * @deprecated - Microphone removed, keyboard-only input now
 */

// API Base URL - use relative paths (Flask serves both frontend and backend)
// This works when Flask is serving the static files
const API_BASE_URL = '';

// Test that script is executing - add visual indicator
if (typeof window !== 'undefined') {
  window.tamilListeningModuleLoaded = true;
  console.log("✅ Module initialization flag set");

  // Add a small indicator in the page to show script loaded
  document.addEventListener("DOMContentLoaded", () => {
    const indicator = document.createElement("div");
    indicator.id = "script-loaded-indicator";
    indicator.style.cssText = "position: fixed; top: 10px; right: 10px; background: #198754; color: white; padding: 5px 10px; border-radius: 4px; font-size: 12px; z-index: 10000; display: none;";
    indicator.textContent = "✓ Script Loaded";
    document.body.appendChild(indicator);
    setTimeout(() => {
      indicator.style.display = "block";
      setTimeout(() => indicator.style.display = "none", 2000);
    }, 100);
  });
}

const levelAudioMap = {
  1: "level1_classroom_tamil",
  2: "level2", // Use level2.mp4 file
  3: "level3audio",
};

let currentLevel = 1; // Default level, will be updated from URL parameter in DOMContentLoaded

let currentAudioId = null;
let remainingGlobalTestTime = null; // Track remaining global test time (if applicable)
let globalTimerInterval = null; // Store the timer interval ID
let currentQuestions = [];
let selectedSpeaker = null; // Stores selected MCQ option for Level 2 Question 1
let audioPlayCount = 0; // Track audio playback count (max 2)
let audioPlayCountKey = null; // Key for storing play count per level
let level2Answers = {
  identify_speaker: null,
  dialogue_ordering: null,
  main_problem_discussed: null,
  match_speaker_role: null,
  long_answers: {}
};

// Level 3 answers storage
// Note: Q1 (identify_emotion MCQ) has been removed
// UI displays: Q1, Q2, Q3, Q4 (4 questions total)
// Internal IDs: "2" (next_action), "3" (fill_missing_phrase), "4" and "5" (long_answers)
let level3NextActionAnswer = null; // Stores answer for Q1 in UI (ID "1")
let level3MissingPhraseAnswer = null; // Stores answer for Q2 in UI (ID "2")
let level3Answers = {
  next_action: null, // Q1 in UI (internal ID "2"): Short answer for next action
  fill_missing_phrase: null, // Q2 in UI (internal ID "3"): Fill in missing phrase
  long_answers: {} // Q3-Q4 in UI (internal IDs "4" and "5"): Long answer questions (keyed by question ID)
};

// Initialize elements - will be set in DOMContentLoaded
let el = {};


function initializeElements() {
  el = {
    audioPlayer: document.getElementById("audio-player"),
    audioStatus: document.getElementById("audio-status"),
    questions: document.getElementById("questions-container"),
    submitBtn: document.getElementById("submit-btn"),
    resultCard: document.getElementById("result-card"),
    resultSummary: document.getElementById("result-summary"),
    resultDetails: document.getElementById("result-details"),
    levelBtns: document.querySelectorAll(".level-btn"),
    nextLevelBtn: document.getElementById("next-level-btn"),
    playAudioBtn: document.getElementById("play-audio-btn"),
    playInstruction: document.getElementById("play-instruction"),
    resultActions: document.querySelector(".result-actions"),
  };
  console.log("📋 Elements initialized:", {
    audioPlayer: !!el.audioPlayer,
    audioStatus: !!el.audioStatus,
    questions: !!el.questions,
    submitBtn: !!el.submitBtn,
    resultCard: !!el.resultCard,
    resultSummary: !!el.resultSummary,
    resultDetails: !!el.resultDetails,
    nextLevelBtn: !!el.nextLevelBtn,
    levelBtns: el.levelBtns ? el.levelBtns.length : 0,
    playAudioBtn: !!el.playAudioBtn,
    playInstruction: !!el.playInstruction
  });
}

function msg(target, text, color = "#5b6cf0") {
  if (!target) return;
  target.textContent = text;
  target.style.color = color;
}

function setActive(level) {
  el.levelBtns.forEach((b) =>
    b.classList.toggle("active", Number(b.dataset.level) === level)
  );
}

function normalizeQuestions(data) {
  if (!data) return [];
  if (Array.isArray(data)) return data;
  if (Array.isArray(data.questions)) return data.questions;
  return [];
}

// Helper function to get marks for a question based on level and question number
function getQuestionMarks(level, questionNumber, questionId) {
  if (level === 1) {
    // Level 1: All questions are 1 mark each
    return 1;
  } else if (level === 2) {
    // Level 2: Q1=1, Q2=1, Q3=2, Q4=3
    const marksMap = { "1": 1, "2": 1, "3": 2, "4": 3 };
    return marksMap[questionId] || marksMap[questionNumber] || 1;
  } else if (level === 3) {
    // Level 3: Q1=2, Q2=2, Q3=2, Q4=3
    const marksMap = { "1": 2, "2": 2, "3": 2, "4": 3 };
    return marksMap[questionId] || marksMap[questionNumber] || 2;
  }
  return 1; // Default
}

// Helper function to render question text with bold Tamil and italic English
function renderQuestionText(questionObj, questionNumber, marks = null) {
  // Validate questionNumber - ensure it's a valid number
  // This prevents errors if undefined/null/undefined variable is passed
  if (typeof questionNumber === 'undefined' || questionNumber === null) {
    console.error("❌ renderQuestionText: questionNumber is undefined or null", questionObj);
    questionNumber = 0; // Fallback to 0 to prevent template string errors
  }

  // Convert to number if it's not already
  const num = Number(questionNumber);
  if (isNaN(num)) {
    console.error("❌ renderQuestionText: questionNumber is not a valid number", questionNumber, questionObj);
    questionNumber = 0; // Fallback to 0
  } else {
    questionNumber = num;
  }

  // Get marks if not provided
  if (marks === null) {
    marks = getQuestionMarks(currentLevel, questionNumber, questionObj.id);
  }

  // Handle both Level 1 (uses 'question' field) and Level 2/3 (uses 'question_text_tamil' field)
  const tamilText = questionObj.question_text_tamil || questionObj.question || "";
  const englishText = questionObj.question_text_english || "";

  let html = `Q${questionNumber}. `;

  // Tamil text in bold
  if (tamilText) {
    html += `<strong>${tamilText}</strong>`;
  } else if (englishText) {
    // Fallback to English if Tamil not available
    html += englishText;
  }

  // Add marks display
  html += ` <span style="color: #666; font-weight: 600; font-size: 0.9em; margin-left: 8px;">[${marks} mark${marks > 1 ? 's' : ''}]</span>`;

  // English translation below in italic/muted style (if available and different from Tamil)
  if (englishText && tamilText) {
    html += `<div style="color: #6c757d; font-size: 0.9em; font-style: italic; margin-top: 6px; padding-left: 0; line-height: 1.4;">${englishText}</div>`;
  }

  return html;
}

function renderQuestions(questions) {
  if (!el.questions) {
    console.error("❌ Questions container element not found!");
    return;
  }

  // Level 2: Render Level 2 specific questions (ONLY when currentLevel === 2)
  // Level 2 questions are gated here to prevent rendering when Level 3 is selected
  if (currentLevel === 2) {
    console.log("🎨 Rendering Level 2 questions...");
    // Reset level2Answers object when loading Level 2
    level2Answers = {
      identify_speaker: null,
      dialogue_ordering: null,
      main_problem_discussed: null,
      match_speaker_role: null,
      long_answers: {}
    };
    currentQuestions = questions;
    el.questions.innerHTML = ""; // Clear loading message
    renderLevel2Questions(questions);
    return;
  }

  // Level 3: Render Level 3 specific questions (ONLY when currentLevel === 3)
  // Level 3 Question Order:
  // Note: Q1 (MCQ – Identifying the emotion) has been removed
  // 1. Short answer – Next action (inference) (Q2 in JSON, displayed as Q1)
  // 2. Fill in the missing phrase (Q3 in JSON, displayed as Q2)
  // 3-4. Long answer questions (Q4-Q5 in JSON, displayed as Q3-Q4)
  if (currentLevel === 3) {
    console.log("🎨 Rendering Level 3 questions...");
    // Reset level3Answers object when loading Level 3
    // Note: Q1 (identify_emotion MCQ) has been removed
    level3Answers = {
      next_action: null,
      fill_missing_phrase: null,
      long_answers: {}
    };
    currentQuestions = questions;
    el.questions.innerHTML = ""; // Clear loading message
    renderLevel3Questions(questions);
    return;
  }

  if (!questions || !Array.isArray(questions) || questions.length === 0) {
    console.error("❌ Invalid or empty questions array:", questions);
    el.questions.innerHTML = "<p style='color: #c0392b; padding: 20px;'>No questions available.</p>";
    return;
  }

  console.log(`🎨 Rendering ${questions.length} questions...`);
  currentQuestions = questions;
  el.questions.innerHTML = ""; // Clear loading message

  questions.forEach((q, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "question";
    wrap.dataset.questionId = q.id;

    const label = document.createElement("label");
    label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
    const marks = getQuestionMarks(1, idx + 1, q.id);
    label.innerHTML = renderQuestionText(q, idx + 1, marks);
    wrap.appendChild(label);

    // Multiple-choice questions: render radio buttons for each option
    if (q.type === "mcq" && Array.isArray(q.options)) {
      const optionsContainer = document.createElement("div");
      optionsContainer.className = "mcq-options";

      q.options.forEach((opt, optIdx) => {
        const optId = `${q.id}_opt_${optIdx}`;

        const optWrap = document.createElement("div");
        optWrap.className = "mcq-option";

        const radio = document.createElement("input");
        radio.type = "radio";
        radio.name = q.id;
        radio.value = opt;
        radio.id = optId;

        // Auto-save on radio button change
        radio.addEventListener("change", () => {
          autoSaveAnswers();
        });

        const optLabel = document.createElement("label");
        optLabel.htmlFor = optId;
        optLabel.textContent = opt;

        optWrap.appendChild(radio);
        optWrap.appendChild(optLabel);
        optionsContainer.appendChild(optWrap);
      });

      wrap.appendChild(optionsContainer);
    } else {
      // Text-based answers: input or textarea
      const isOrdering =
        q.type === "ordering" || q.type === "dialogue-ordering";

      // For ordering questions, render draggable items
      if (isOrdering && Array.isArray(q.options)) {
        const orderingContainer = document.createElement("div");
        orderingContainer.className = "ordering-container";
        orderingContainer.dataset.questionId = q.id;

        // Instruction text
        const instruction = document.createElement("div");
        instruction.className = "ordering-instruction";
        instruction.textContent = "Drag and drop to reorder:";
        orderingContainer.appendChild(instruction);

        // Create draggable list
        const listContainer = document.createElement("div");
        listContainer.className = "ordering-list";

        // Shuffle options for initial display (so user has to order them)
        const shuffledOptions = [...q.options].sort(() => Math.random() - 0.5);

        shuffledOptions.forEach((option, idx) => {
          const item = document.createElement("div");
          item.className = "ordering-item";
          item.draggable = true;
          item.dataset.value = option;
          item.textContent = option;

          // Add drag handle indicator
          const handle = document.createElement("span");
          handle.className = "drag-handle";
          handle.textContent = "☰";
          item.insertBefore(handle, item.firstChild);

          listContainer.appendChild(item);
        });

        orderingContainer.appendChild(listContainer);
        wrap.appendChild(orderingContainer);

        // Initialize drag and drop for this container
        initDragAndDrop(listContainer);
      } else {
        // Regular text input
        const input = document.createElement("input");
        input.type = "text"; // Explicitly set type to "text"
        input.name = q.id;
        input.placeholder = "Type your answer";

        // Level 1, Question 3: numeric-only with numeric keyboard
        if (currentLevel === 1 && String(q.id) === "3" && !isOrdering) {
          input.inputMode = "numeric";
          input.pattern = "[0-9]*";

          // Restrict to digits only and auto-save
          input.addEventListener("input", () => {
            input.value = input.value.replace(/[^0-9]/g, "");
            // Auto-save to localStorage
            autoSaveAnswers();
          });

          // Instruction text
          const hint = document.createElement("div");
          hint.className = "question-hint";
          hint.textContent =
            "Numbers only (0-9). Use the numeric keypad below for this question.";
          wrap.appendChild(hint);

          // Numeric keyboard (0-9 + backspace, clear)
          const numKb = document.createElement("div");
          numKb.className = "numeric-keyboard";
          numKb.id = `numeric-kb-level1-${q.id}`; // Unique ID to prevent duplicates
          const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "⌫", "Clear"];
          keys.forEach((k) => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "numeric-key";
            btn.textContent = k;
            numKb.appendChild(btn);
          });
          wrap.appendChild(input);
          wrap.appendChild(numKb);

          // Mark input as numeric to prevent Tamil keyboard
          input.classList.add("numeric-input");

          // Prevent Tamil keyboard from showing for this input
          input.addEventListener("focus", (e) => {
            e.stopPropagation(); // Prevent Tamil keyboard from showing
          });

          numKb.addEventListener("click", (e) => {
            const btn = e.target.closest(".numeric-key");
            if (!btn) return;
            const key = btn.textContent;
            if (key === "⌫") {
              input.value = input.value.slice(0, -1);
            } else if (key === "Clear") {
              input.value = "";
            } else {
              input.value = (input.value || "") + key;
            }
            input.focus();
            // Auto-save to localStorage
            autoSaveAnswers();
          });
        } else {
          // Default: Tamil keyboard for non-numeric text inputs
          input.addEventListener("focus", () => {
            if (window.TamilKeyboard) {
              if (!input._tamilKeyboardInstance) {
                input._tamilKeyboardInstance = new window.TamilKeyboard(input);
              }
              input._tamilKeyboardInstance.show();
            }
          });
          // Auto-save on input
          input.addEventListener("input", () => {
            autoSaveAnswers();
          });
          wrap.appendChild(input);
        }
      }
    }

    // Append question to container (for all question types)
    el.questions.appendChild(wrap);
  });
}

// Level 2 specific question rendering
function renderLevel2Questions(questions) {
  // Safety check: Only render Level 2 questions when currentLevel === 2
  if (currentLevel !== 2) {
    console.warn("⚠️ renderLevel2Questions called but currentLevel is not 2. Skipping Level 2 rendering.");
    return;
  }

  if (!questions || !Array.isArray(questions) || questions.length === 0) {
    console.error("❌ Invalid or empty Level 2 questions array");
    el.questions.innerHTML = "<p style='color: #c0392b; padding: 20px;'>No Level 2 questions available.</p>";
    return;
  }

  questions.forEach((q, idx) => {
    // Question 1: MCQ
    if (q.id === "1" && q.type === "mcq") {
      // Reset selectedSpeaker and level2Answers when rendering Question 1
      selectedSpeaker = null;
      level2Answers.identify_speaker = null;

      const wrap = document.createElement("div");
      wrap.className = "question level2-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "mcq";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
      const marks = getQuestionMarks(2, idx + 1, q.id);
      label.innerHTML = renderQuestionText(q, idx + 1, marks);
      wrap.appendChild(label);

      // Tamil sentence display (the quote)
      const tamilSentence = document.createElement("div");
      tamilSentence.className = "tamil-sentence-quote";
      tamilSentence.style.cssText = `
        background: #f8f9fa;
        padding: 14px 16px;
        margin: 12px 0;
        border-left: 4px solid #667eea;
        border-radius: 6px;
        font-size: 1.05em;
        color: #212529;
        line-height: 1.6;
        font-weight: 500;
      `;
      tamilSentence.textContent = `"${q.sentence_tamil || ""}"`;
      wrap.appendChild(tamilSentence);

      // English reference text (non-editable, read-only)
      const englishReference = document.createElement("div");
      englishReference.className = "english-reference";
      englishReference.style.cssText = `
        background: #e9ecef;
        padding: 10px 14px;
        margin: 8px 0 16px 0;
        border-radius: 4px;
        font-size: 0.9em;
        color: #6c757d;
        font-style: italic;
        border: 1px solid #dee2e6;
      `;
      englishReference.textContent = `(Reference: ${q.sentence_english || ""})`;
      wrap.appendChild(englishReference);

      // MCQ Options container
      const optionsContainer = document.createElement("div");
      optionsContainer.className = "mcq-options level2-mcq-options";

      if (Array.isArray(q.options)) {
        q.options.forEach((opt, optIdx) => {
          const optId = `level2_q1_opt_${optIdx}`;

          const optWrap = document.createElement("div");
          optWrap.className = "mcq-option level2-mcq-option";
          optWrap.style.cssText = "margin: 8px 0; padding: 10px; border: 2px solid #dee2e6; border-radius: 6px; cursor: pointer; transition: all 0.2s;";

          // Hover effect
          optWrap.addEventListener("mouseenter", () => {
            optWrap.style.borderColor = "#667eea";
            optWrap.style.backgroundColor = "#f0f4ff";
          });
          optWrap.addEventListener("mouseleave", () => {
            const radio = optWrap.querySelector('input[type="radio"]');
            if (!radio?.checked) {
              optWrap.style.borderColor = "#dee2e6";
              optWrap.style.backgroundColor = "transparent";
            }
          });

          const radio = document.createElement("input");
          radio.type = "radio";
          radio.name = "level2_q1_mcq"; // All options share the same name (only one selectable)
          radio.value = opt;
          radio.id = optId;

          // Update styling and capture selection when selected
          radio.addEventListener("change", () => {
            document.querySelectorAll(".level2-mcq-option").forEach(opt => {
              opt.style.borderColor = "#dee2e6";
              opt.style.backgroundColor = "transparent";
            });
            if (radio.checked) {
              optWrap.style.borderColor = "#198754";
              optWrap.style.backgroundColor = "#d1e7dd";
              // Capture selected option in selectedSpeaker variable
              selectedSpeaker = radio.value;
              // Store in level2Answers object
              level2Answers.identify_speaker = selectedSpeaker;
              console.log("📝 Selected speaker:", selectedSpeaker);
              console.log("💾 Updated level2Answers.identify_speaker:", level2Answers.identify_speaker);
              // Auto-save to localStorage
              autoSaveAnswers();
            }
          });

          const optLabel = document.createElement("label");
          optLabel.htmlFor = optId;
          optLabel.textContent = opt;
          optLabel.style.cssText = "cursor: pointer; margin-left: 8px; font-size: 1em;";

          // Make entire option clickable
          optWrap.addEventListener("click", (e) => {
            if (e.target !== radio) {
              radio.checked = true;
              radio.dispatchEvent(new Event("change"));
            }
          });

          optWrap.appendChild(radio);
          optWrap.appendChild(optLabel);
          optionsContainer.appendChild(optWrap);
        });
      }

      wrap.appendChild(optionsContainer);
      el.questions.appendChild(wrap);
    }

    // Question 2: Dialogue Ordering
    if (q.id === "2" && q.type === "dialogue_ordering") {
      const wrap = document.createElement("div");
      wrap.className = "question level2-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "dialogue_ordering";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
      const marks = getQuestionMarks(2, idx + 1, q.id);
      label.innerHTML = renderQuestionText(q, idx + 1, marks);
      wrap.appendChild(label);

      // Note: English translation is now included in the question label via renderQuestionText()

      // Dialogue ordering container
      const orderingContainer = document.createElement("div");
      orderingContainer.className = "dialogue-ordering-container level2-dialogue-ordering";
      orderingContainer.dataset.questionId = q.id;
      orderingContainer.style.cssText = "margin-top: 16px;";

      // Create draggable list container
      const listContainer = document.createElement("div");
      listContainer.className = "dialogue-ordering-list";
      listContainer.style.cssText = "display: flex; flex-direction: column; gap: 12px;";

      // Get items from question data
      const items = Array.isArray(q.items) ? q.items : [];

      // Shuffle items for initial display (so user has to order them)
      const shuffledItems = [...items].sort(() => Math.random() - 0.5);

      // Create draggable boxes for each sentence
      shuffledItems.forEach((itemText, itemIdx) => {
        // Assign unique data-id (1 to 6) based on original index
        const originalIndex = items.indexOf(itemText);
        const dataId = originalIndex + 1; // 1 to 6

        const item = document.createElement("div");
        item.className = "dialogue-ordering-item level2-ordering-item";
        item.draggable = true;
        item.dataset.itemId = dataId; // Unique data-id (1 to 6)
        item.dataset.itemText = itemText;
        item.dataset.originalIndex = originalIndex;
        item.style.cssText = `
          padding: 14px 18px;
          background: #ffffff;
          border: 2px solid #dee2e6;
          border-radius: 8px;
          cursor: move;
          transition: all 0.2s;
          user-select: none;
          position: relative;
          min-height: 60px;
          display: flex;
          align-items: center;
          font-size: 0.95em;
          line-height: 1.5;
        `;
        item.textContent = itemText;

        // Add drag handle indicator
        const handle = document.createElement("span");
        handle.className = "drag-handle";
        handle.style.cssText = "margin-right: 12px; font-size: 1.3em; color: #6c757d; cursor: grab; user-select: none;";
        handle.textContent = "☰";
        item.insertBefore(handle, item.firstChild);

        // Hover effect
        item.addEventListener("mouseenter", () => {
          if (!item.classList.contains("dragging")) {
            item.style.borderColor = "#667eea";
            item.style.boxShadow = "0 2px 8px rgba(102, 126, 234, 0.15)";
          }
        });
        item.addEventListener("mouseleave", () => {
          if (!item.classList.contains("dragging") && !item.classList.contains("drag-over")) {
            item.style.borderColor = "#dee2e6";
            item.style.boxShadow = "none";
          }
        });

        listContainer.appendChild(item);
      });

      orderingContainer.appendChild(listContainer);
      wrap.appendChild(orderingContainer);
      el.questions.appendChild(wrap);

      // Initialize drag and drop for this container
      initLevel2DragAndDrop(listContainer);
    }

    // Question 3: Short Answer - Enhanced Professional UI/UX
    if (q.id === "3" && q.type === "short_answer") {
      const wrap = document.createElement("div");
      wrap.className = "question level2-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "short_answer";
      wrap.style.cssText = `
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e9ecef;
        transition: all 0.3s ease;
      `;

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = `
        display: block;
        margin-bottom: 16px;
        font-weight: 600;
        font-size: 1.15em;
        color: #2c3e50;
        line-height: 1.5;
      `;
      const marks = getQuestionMarks(2, idx + 1, q.id);
      label.innerHTML = renderQuestionText(q, idx + 1, marks);
      wrap.appendChild(label);

      // Tamil instruction text - Enhanced styling
      if (q.instruction_tamil) {
        const instructionContainer = document.createElement("div");
        instructionContainer.style.cssText = `
          background: #f8f9fa;
          border-left: 4px solid #667eea;
          padding: 12px 16px;
          border-radius: 6px;
          margin-bottom: 20px;
        `;

        const instruction = document.createElement("div");
        instruction.className = "tamil-instruction-text";
        instruction.style.cssText = `
          color: #495057;
          font-size: 0.95em;
          font-weight: 500;
          line-height: 1.6;
        `;
        instruction.textContent = q.instruction_tamil;
        instructionContainer.appendChild(instruction);
        wrap.appendChild(instructionContainer);
      }

      // Answer container with enhanced styling
      const answerContainer = document.createElement("div");
      answerContainer.style.cssText = `
        position: relative;
        margin-bottom: 12px;
      `;

      // Multiline textarea for answer - Professional styling
      const textarea = document.createElement("textarea");
      textarea.name = "level2_q3_short_answer";
      textarea.id = "level2_q3_textarea";
      textarea.className = "level2-short-answer-textarea";
      textarea.placeholder = "உங்கள் பதிலை இங்கே தட்டச்சு செய்யவும்...\n\nType your answer here...";
      textarea.rows = 6;
      textarea.style.cssText = `
        width: 100%;
        padding: 16px 18px;
        border: 2px solid #dee2e6;
        border-radius: 8px;
        font-size: 1.05em;
        font-family: "Noto Sans Tamil", "Segoe UI", Arial, sans-serif;
        resize: vertical;
        transition: all 0.3s ease;
        box-sizing: border-box;
        line-height: 1.7;
        color: #2c3e50;
        background: #ffffff;
        min-height: 150px;
      `;

      // Enhanced focus effect
      textarea.addEventListener("focus", () => {
        textarea.style.borderColor = "#667eea";
        textarea.style.outline = "none";
        textarea.style.boxShadow = "0 0 0 4px rgba(102, 126, 234, 0.15), 0 4px 12px rgba(102, 126, 234, 0.1)";
        textarea.style.background = "#fafbff";
        wrap.style.boxShadow = "0 4px 16px rgba(102, 126, 234, 0.15)";
        wrap.style.borderColor = "#667eea";
      });

      textarea.addEventListener("blur", () => {
        textarea.style.borderColor = "#dee2e6";
        textarea.style.boxShadow = "none";
        textarea.style.background = "#ffffff";
        wrap.style.boxShadow = "0 2px 8px rgba(0, 0, 0, 0.08)";
        wrap.style.borderColor = "#e9ecef";
      });

      // Tamil keyboard support
      textarea.addEventListener("focus", () => {
        if (window.TamilKeyboard) {
          if (!textarea._tamilKeyboardInstance) {
            textarea._tamilKeyboardInstance = new window.TamilKeyboard(textarea);
          }
          textarea._tamilKeyboardInstance.show();
        }
      });

      answerContainer.appendChild(textarea);

      // Microphone is available in the keyboard - no need for separate mic button in answer box
      wrap.appendChild(answerContainer);

      // Enhanced character and word count indicator
      const statsContainer = document.createElement("div");
      statsContainer.style.cssText = `
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        padding: 10px 12px;
        background: #f8f9fa;
        border-radius: 6px;
        font-size: 0.9em;
      `;

      const charCount = document.createElement("div");
      charCount.className = "char-count-indicator";
      charCount.style.cssText = `
        color: #6c757d;
        font-weight: 500;
      `;

      const wordCount = document.createElement("div");
      wordCount.className = "word-count-indicator";
      wordCount.style.cssText = `
        color: #6c757d;
        font-weight: 500;
      `;

      const updateStats = () => {
        const text = textarea.value.trim();
        const charCountValue = text.length;
        const wordCountValue = text ? text.split(/\s+/).filter(word => word.length > 0).length : 0;

        charCount.innerHTML = `
          <span style="color: #667eea; font-weight: 600;">${charCountValue}</span>
          <span style="color: #6c757d;"> எழுத்துகள்</span>
          <span style="color: #adb5bd; margin: 0 4px;">|</span>
          <span style="color: #667eea; font-weight: 600;">${charCountValue}</span>
          <span style="color: #6c757d;"> characters</span>
        `;

        wordCount.innerHTML = `
          <span style="color: #667eea; font-weight: 600;">${wordCountValue}</span>
          <span style="color: #6c757d;"> சொற்கள்</span>
          <span style="color: #adb5bd; margin: 0 4px;">|</span>
          <span style="color: #667eea; font-weight: 600;">${wordCountValue}</span>
          <span style="color: #6c757d;"> words</span>
        `;
      };

      textarea.addEventListener("input", () => {
        updateStats();
        // Store in level2Answers object
        level2Answers.main_problem_discussed = textarea.value.trim();
        // Auto-save to localStorage
        autoSaveAnswers();
      });
      updateStats(); // Initial count

      statsContainer.appendChild(charCount);
      statsContainer.appendChild(wordCount);
      wrap.appendChild(statsContainer);

      // Helper text
      const helperText = document.createElement("div");
      helperText.style.cssText = `
        margin-top: 12px;
        padding: 10px 14px;
        background: #e7f3ff;
        border-left: 3px solid #0d6efd;
        border-radius: 4px;
        font-size: 0.9em;
        color: #004085;
        line-height: 1.6;
      `;
      helperText.innerHTML = `
        <strong>💡 உதவி:</strong> உங்கள் பதிலை 1 அல்லது 2 வாக்கியங்களில் தெளிவாக எழுதவும். 
        <span style="color: #6c757d;">Write your answer clearly in 1 or 2 sentences.</span>
      `;
      wrap.appendChild(helperText);

      el.questions.appendChild(wrap);
    }

    // Question 4: Match Speaker Role - Using Dropdown/Select Interface (No Drag & Drop)
    if (q.id === "4" && q.type === "match_speaker_role") {
      const wrap = document.createElement("div");
      wrap.className = "question level2-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "match_speaker_role";
      wrap.style.cssText = `
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        border: 1px solid #e9ecef;
      `;

      // Question label with Tamil text
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = `
        display: block;
        margin-bottom: 16px;
        font-weight: 600;
        font-size: 1.15em;
        color: #2c3e50;
        line-height: 1.5;
      `;
      const marks = getQuestionMarks(2, idx + 1, q.id);
      label.innerHTML = renderQuestionText(q, idx + 1, marks);
      wrap.appendChild(label);

      // Tamil instruction text
      if (q.instruction_tamil) {
        const instruction = document.createElement("div");
        instruction.className = "tamil-instruction-text";
        instruction.style.cssText = `
          background: #f8f9fa;
          border-left: 4px solid #667eea;
          padding: 12px 16px;
          border-radius: 6px;
          margin-bottom: 20px;
          color: #495057;
          font-size: 0.95em;
          font-weight: 500;
          line-height: 1.6;
        `;
        instruction.textContent = q.instruction_tamil;
        wrap.appendChild(instruction);
      }

      // Get speakers and roles from question data
      const speakers = Array.isArray(q.speakers) ? q.speakers : [];
      const roleDescriptions = Array.isArray(q.roles) ? q.roles : [];

      // Create matching container with vertical layout
      const matchingContainer = document.createElement("div");
      matchingContainer.className = "speaker-role-matching-container";
      matchingContainer.style.cssText = `
        display: flex;
        flex-direction: column;
        gap: 20px;
        margin-top: 16px;
      `;

      // Create a card for each speaker with dropdown
      speakers.forEach((speaker, speakerIdx) => {
        const speakerCard = document.createElement("div");
        speakerCard.className = "speaker-role-card";
        speakerCard.dataset.speaker = speaker;
        speakerCard.style.cssText = `
          background: #ffffff;
          border: 2px solid #e9ecef;
          border-radius: 10px;
          padding: 20px;
          transition: all 0.3s ease;
        `;

        // Speaker name header
        const speakerHeader = document.createElement("div");
        speakerHeader.style.cssText = `
          display: flex;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 2px solid #f0f0f0;
        `;

        const speakerLabel = document.createElement("div");
        speakerLabel.style.cssText = `
          font-weight: 700;
          font-size: 1.2em;
          color: #2c3e50;
          flex: 1;
        `;
        speakerLabel.textContent = speaker;

        const speakerNumber = document.createElement("div");
        speakerNumber.style.cssText = `
          background: #667eea;
          color: white;
          width: 32px;
          height: 32px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 0.9em;
          margin-right: 12px;
        `;
        speakerNumber.textContent = speakerIdx + 1;

        speakerHeader.appendChild(speakerNumber);
        speakerHeader.appendChild(speakerLabel);
        speakerCard.appendChild(speakerHeader);

        // Role selection dropdown
        const selectContainer = document.createElement("div");
        selectContainer.style.cssText = `
          position: relative;
        `;

        const selectLabel = document.createElement("label");
        selectLabel.style.cssText = `
          display: block;
          margin-bottom: 8px;
          font-weight: 600;
          color: #495057;
          font-size: 0.95em;
        `;
        selectLabel.textContent = "பாத்திர விளக்கம் தேர்ந்தெடுக்கவும் / Select Role:";
        selectContainer.appendChild(selectLabel);

        const select = document.createElement("select");
        select.className = "speaker-role-select";
        select.dataset.speaker = speaker;
        select.style.cssText = `
          width: 100%;
          padding: 14px 16px;
          border: 2px solid #dee2e6;
          border-radius: 8px;
          font-size: 1em;
          font-family: "Noto Sans Tamil", "Segoe UI", Arial, sans-serif;
          background: #ffffff;
          color: #2c3e50;
          cursor: pointer;
          transition: all 0.3s ease;
          appearance: none;
          background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23667eea' d='M6 9L1 4h10z'/%3E%3C/svg%3E");
          background-repeat: no-repeat;
          background-position: right 16px center;
          background-size: 12px;
          padding-right: 40px;
        `;

        // Default option
        const defaultOption = document.createElement("option");
        defaultOption.value = "";
        defaultOption.textContent = "பாத்திர விளக்கம் தேர்ந்தெடுக்கவும் / Select a role...";
        defaultOption.disabled = true;
        defaultOption.selected = true;
        select.appendChild(defaultOption);

        // Add all roles as options
        roleDescriptions.forEach((roleText) => {
          const option = document.createElement("option");
          option.value = roleText;
          option.textContent = roleText;
          select.appendChild(option);
        });

        // Change handler
        select.addEventListener("change", function () {
          const selectedRole = this.value;

          // Update visual state
          if (selectedRole) {
            this.style.borderColor = "#198754";
            this.style.background = "#f0f9f4";
            speakerCard.style.borderColor = "#198754";
            speakerCard.style.background = "#f8fff9";
          } else {
            this.style.borderColor = "#dee2e6";
            this.style.background = "#ffffff";
            speakerCard.style.borderColor = "#e9ecef";
            speakerCard.style.background = "#ffffff";
          }

          // Update mapping
          updateSpeakerRoleMappingFromSelects(matchingContainer);
          // Auto-save to localStorage
          autoSaveAnswers();
        });

        // Focus effect
        select.addEventListener("focus", function () {
          this.style.borderColor = "#667eea";
          this.style.boxShadow = "0 0 0 4px rgba(102, 126, 234, 0.1)";
          speakerCard.style.borderColor = "#667eea";
        });

        select.addEventListener("blur", function () {
          if (!this.value) {
            this.style.borderColor = "#dee2e6";
            this.style.boxShadow = "none";
            speakerCard.style.borderColor = "#e9ecef";
          }
        });

        selectContainer.appendChild(select);
        speakerCard.appendChild(selectContainer);
        matchingContainer.appendChild(speakerCard);
      });

      wrap.appendChild(matchingContainer);
      el.questions.appendChild(wrap);
    }

    // Question 5: Long Answer (Level 2) - REMOVED
    // Level 2 now only renders Q1-Q4 (4 questions total)
    /*
    if (q.type === "long_answer") {
      // Initialize long_answers object if needed
      if (!level2Answers.long_answers) {
        level2Answers.long_answers = {};
      }
      // Reset this specific long answer when rendering
      level2Answers.long_answers[q.id] = null;
      
      const wrap = document.createElement("div");
      wrap.className = "question level2-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "long_answer";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
      label.innerHTML = renderQuestionText(q, idx + 1);
      wrap.appendChild(label);

      // Tamil instruction text
      if (q.instruction_tamil) {
        const instruction = document.createElement("div");
        instruction.className = "tamil-instruction-text";
        instruction.style.cssText = `
          color: #6c757d;
          font-size: 0.9em;
          font-style: italic;
          margin: 4px 0 8px 0;
        `;
        instruction.textContent = q.instruction_tamil;
        wrap.appendChild(instruction);
      }

      // Note: English translation is now included in the question label via renderQuestionText()

      // Large textarea for long answer
      const textarea = document.createElement("textarea");
      textarea.name = `level2_q${q.id}_long_answer`;
      textarea.id = `level2_q${q.id}_textarea`;
      textarea.className = "level2-long-answer-textarea";
      textarea.placeholder = "உங்கள் பதிலை இங்கே தட்டச்சு செய்யவும் / Type your answer here";
      textarea.rows = 8;
      textarea.style.cssText = `
        width: 100%;
        padding: 12px;
        border: 2px solid #dee2e6;
        border-radius: 6px;
        font-size: 1em;
        font-family: inherit;
        resize: vertical;
        transition: border-color 0.2s;
        box-sizing: border-box;
        min-height: 150px;
      `;
      
      // Focus effect
      textarea.addEventListener("focus", () => {
        textarea.style.borderColor = "#667eea";
        textarea.style.outline = "none";
        textarea.style.boxShadow = "0 0 0 3px rgba(102, 126, 234, 0.1)";
      });
      
      textarea.addEventListener("blur", () => {
        textarea.style.borderColor = "#dee2e6";
        textarea.style.boxShadow = "none";
      });

      // Tamil keyboard support
      textarea.addEventListener("focus", () => {
        if (window.TamilKeyboard) {
          if (!textarea._tamilKeyboardInstance) {
            textarea._tamilKeyboardInstance = new window.TamilKeyboard(textarea);
          }
          textarea._tamilKeyboardInstance.show();
        }
      });

      // Character count indicator
      const charCount = document.createElement("div");
      charCount.className = "char-count-indicator";
      charCount.style.cssText = "margin-top: 6px; font-size: 0.85em; color: #6c757d; text-align: right;";
      
      const updateCharCount = () => {
        const count = textarea.value.length;
        charCount.textContent = `${count} எழுத்துகள் / ${count} characters`;
      };
      
      // Capture user's answer and store in level2Answers by question ID
      textarea.addEventListener("input", () => {
        // Read textarea value, trim leading and trailing whitespace
        const userAnswer = textarea.value.trim();
        // Store in level2Answers.long_answers object keyed by question ID
        level2Answers.long_answers[q.id] = userAnswer;
        console.log(`📝 Level 2 Long Answer Q${q.id}:`, userAnswer);
        console.log(`💾 Updated level2Answers.long_answers[${q.id}]:`, level2Answers.long_answers[q.id]);
        // Update character count
        updateCharCount();
      });
      
      updateCharCount(); // Initial count

      wrap.appendChild(textarea);
      wrap.appendChild(charCount);
      el.questions.appendChild(wrap);
    }
    */
  });
}

// Function to update speaker-to-role mapping (for dropdown/select interface)
function updateSpeakerRoleMappingFromSelects(container) {
  const selects = container.querySelectorAll('.speaker-role-select');
  const speakerRoleMapping = {};

  selects.forEach(select => {
    const speaker = select.dataset.speaker;
    const selectedRole = select.value;

    if (selectedRole && selectedRole.trim() !== "") {
      speakerRoleMapping[speaker] = selectedRole.trim();
    }
  });

  // Store speaker-role mapping in level2Answers object under key "match_speaker_role"
  level2Answers.match_speaker_role = Object.keys(speakerRoleMapping).length > 0 ? speakerRoleMapping : null;

  // Log for debugging
  console.log("📋 Updated speaker-role mapping:", speakerRoleMapping);
  console.log("💾 Stored in level2Answers.match_speaker_role:", level2Answers.match_speaker_role);
}

// Legacy function for drag-and-drop (kept for compatibility but not used)
function updateSpeakerRoleMapping(container) {
  const speakerBoxes = container.querySelectorAll('.speaker-box');
  const speakerRoleMapping = {};

  speakerBoxes.forEach(speakerBox => {
    const speaker = speakerBox.dataset.speaker;
    const roleMatchArea = speakerBox.querySelector('.role-match-area[data-role-text]');

    // Check if roleMatchArea exists and has a non-empty roleText
    if (roleMatchArea && roleMatchArea.dataset.roleText && roleMatchArea.dataset.roleText.trim() !== "") {
      const roleText = roleMatchArea.dataset.roleText.trim();
      speakerRoleMapping[speaker] = roleText;
    }
  });

  // Store speaker-role mapping in level2Answers object under key "match_speaker_role"
  level2Answers.match_speaker_role = Object.keys(speakerRoleMapping).length > 0 ? speakerRoleMapping : null;

  // Log for debugging
  console.log("📋 Updated speaker-role mapping:", speakerRoleMapping);
  console.log("💾 Stored in level2Answers.match_speaker_role:", level2Answers.match_speaker_role);
}

// Level 2 speaker-role matching drag and drop handler
function initLevel2SpeakerRoleMatching(container) {
  // Safety check: Only initialize Level 2 drag-and-drop when currentLevel === 2
  if (currentLevel !== 2) {
    console.warn("⚠️ initLevel2SpeakerRoleMatching called but currentLevel is not 2. Skipping initialization.");
    return;
  }

  let draggedRole = null;

  const roleBoxes = container.querySelectorAll(".level2-role-box");
  const speakerBoxes = container.querySelectorAll(".speaker-box");

  // Make role boxes draggable (from roles column)
  roleBoxes.forEach((roleBox) => {
    roleBox.addEventListener("dragstart", function (e) {
      draggedRole = this;
      this.classList.add("dragging");
      this.style.opacity = "0.4";
      this.style.transform = "rotate(2deg) scale(1.05)";
      this.style.boxShadow = "0 8px 16px rgba(0,0,0,0.2)";
      this.style.zIndex = "1000";
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", this.dataset.roleText);
    });

    roleBox.addEventListener("dragend", function () {
      this.classList.remove("dragging");
      // Restore original state based on whether it's assigned
      if (this.classList.contains("assigned")) {
        this.style.opacity = "0.6";
      } else {
        this.style.opacity = "1";
      }
      this.style.transform = "";
      this.style.boxShadow = "";
      this.style.zIndex = "";
      speakerBoxes.forEach(speakerBox => {
        const dropIndicator = speakerBox.querySelector(".drop-indicator");
        if (dropIndicator) {
          dropIndicator.style.display = "none";
        }
        speakerBox.style.borderColor = "";
        speakerBox.style.borderStyle = "";
      });
    });
  });

  // Make matched roles draggable (from speaker boxes)
  // This will be set up dynamically when roles are matched
  function setupMatchedRoleDragging(roleMatchArea) {
    roleMatchArea.addEventListener("dragstart", function (e) {
      const roleText = this.dataset.roleText;
      draggedRole = container.querySelector(`.level2-role-box[data-role-text="${roleText}"]`);
      if (draggedRole) {
        draggedRole.classList.add("dragging");
        draggedRole.style.opacity = "0.4";
        draggedRole.style.transform = "rotate(2deg) scale(1.05)";
        draggedRole.style.boxShadow = "0 8px 16px rgba(0,0,0,0.2)";
        draggedRole.style.zIndex = "1000";
      }
      this.style.opacity = "0.5";
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", roleText);
    });

    roleMatchArea.addEventListener("dragend", function () {
      if (draggedRole) {
        draggedRole.classList.remove("dragging");
        if (draggedRole.classList.contains("assigned")) {
          draggedRole.style.opacity = "0.6";
        } else {
          draggedRole.style.opacity = "1";
        }
        draggedRole.style.transform = "";
        draggedRole.style.boxShadow = "";
        draggedRole.style.zIndex = "";
      }
      this.style.opacity = "1";
      speakerBoxes.forEach(speakerBox => {
        const dropIndicator = speakerBox.querySelector(".drop-indicator");
        if (dropIndicator) {
          dropIndicator.style.display = "none";
        }
        speakerBox.style.borderColor = "";
        speakerBox.style.borderStyle = "";
      });
    });
  }

  // Make speaker boxes drop zones
  speakerBoxes.forEach((speakerBox) => {
    speakerBox.addEventListener("dragover", function (e) {
      if (e.preventDefault) {
        e.preventDefault();
      }
      e.dataTransfer.dropEffect = "move";

      if (draggedRole) {
        const dropIndicator = this.querySelector(".drop-indicator");
        if (dropIndicator) {
          dropIndicator.style.display = "block";
        }
        // Enhanced visual feedback
        this.style.borderColor = "#198754";
        this.style.borderStyle = "solid";
        this.style.borderWidth = "3px";
        this.style.background = "rgba(25, 135, 84, 0.1)";
        this.style.transform = "scale(1.02)";
        this.style.transition = "all 0.2s ease";
      }
      return false;
    });

    speakerBox.addEventListener("dragleave", function () {
      const dropIndicator = this.querySelector(".drop-indicator");
      if (dropIndicator) {
        dropIndicator.style.display = "none";
      }
      // Check if this box has a matched role
      const roleMatchArea = this.querySelector(".role-match-area[data-role-text]");
      if (roleMatchArea && roleMatchArea.dataset.roleText) {
        // Keep matched state
        this.style.borderColor = "#198754";
        this.style.borderStyle = "solid";
        this.style.borderWidth = "2px";
        this.style.background = "#d1e7dd";
      } else {
        // Reset to empty state
        this.style.borderColor = "#dee2e6";
        this.style.borderStyle = "dashed";
        this.style.borderWidth = "2px";
        this.style.background = "#f8f9fa";
      }
      this.style.transform = "";
    });

    speakerBox.addEventListener("drop", function (e) {
      if (e.stopPropagation) {
        e.stopPropagation();
      }

      if (draggedRole) {
        const roleText = draggedRole.dataset.roleText;
        const speaker = this.dataset.speaker;

        // Rule 1: If this speaker already has a role, remove it and restore that role box
        const existingRoleMatchArea = this.querySelector(".role-match-area[data-role-text]");
        if (existingRoleMatchArea && existingRoleMatchArea.dataset.roleText !== roleText) {
          const previousRoleText = existingRoleMatchArea.dataset.roleText;
          // Restore the previous role box (remove assigned state)
          const previousRoleBox = container.querySelector(`.level2-role-box[data-role-text="${previousRoleText}"]`);
          if (previousRoleBox) {
            previousRoleBox.classList.remove("assigned");
            previousRoleBox.style.opacity = "1";
            previousRoleBox.style.borderColor = "#667eea";
            previousRoleBox.style.borderStyle = "solid";
            const assignedIndicator = previousRoleBox.querySelector(".assigned-indicator");
            if (assignedIndicator) {
              assignedIndicator.remove();
            }
          }
        }

        // Rule 2: If this role is already assigned to another speaker, remove it from there
        const allSpeakerBoxes = container.querySelectorAll(".speaker-box");
        allSpeakerBoxes.forEach(otherSpeakerBox => {
          if (otherSpeakerBox !== this) {
            const otherRoleMatchArea = otherSpeakerBox.querySelector(".role-match-area[data-role-text]");
            if (otherRoleMatchArea && otherRoleMatchArea.dataset.roleText === roleText) {
              // Remove role from other speaker
              otherRoleMatchArea.dataset.roleText = "";
              otherRoleMatchArea.textContent = "பாத்திர விளக்கம் இங்கே விடவும் / Drop role here";
              otherRoleMatchArea.style.display = "block";
              otherRoleMatchArea.style.color = "#6c757d";
              otherRoleMatchArea.style.fontStyle = "italic";
              otherRoleMatchArea.style.fontWeight = "400";

              // Reset other speaker box visual state
              otherSpeakerBox.style.borderColor = "#dee2e6";
              otherSpeakerBox.style.borderStyle = "dashed";
              otherSpeakerBox.style.borderWidth = "2px";
              otherSpeakerBox.style.background = "#f8f9fa";

              // Remove drag functionality from the cleared role match area
              const clearedRoleMatchArea = otherSpeakerBox.querySelector(".role-match-area");
              if (clearedRoleMatchArea) {
                clearedRoleMatchArea.draggable = false;
                const dragHandle = clearedRoleMatchArea.querySelector(".drag-handle-small");
                if (dragHandle) {
                  dragHandle.remove();
                }
              }
            }
          }
        });

        // Keep role box visible but mark it as assigned (don't hide it)
        // This allows users to drag it again to shuffle/reassign
        if (draggedRole) {
          draggedRole.classList.add("assigned");
          draggedRole.style.opacity = "0.6";
          draggedRole.style.borderColor = "#6c757d";
          draggedRole.style.borderStyle = "dashed";
          // Add a checkmark indicator
          if (!draggedRole.querySelector(".assigned-indicator")) {
            const indicator = document.createElement("span");
            indicator.className = "assigned-indicator";
            indicator.textContent = "✓";
            indicator.style.cssText = `
              position: absolute;
              top: 4px;
              right: 4px;
              background: #198754;
              color: white;
              border-radius: 50%;
              width: 20px;
              height: 20px;
              display: flex;
              align-items: center;
              justify-content: center;
              font-size: 12px;
              font-weight: bold;
            `;
            draggedRole.style.position = "relative";
            draggedRole.appendChild(indicator);
          }
        }

        // Hide placeholder text and display matched role in this speaker box
        this.textContent = ""; // Clear placeholder text
        const roleMatchArea = this.querySelector(".role-match-area");
        if (roleMatchArea) {
          // Set dataset first
          roleMatchArea.dataset.roleText = roleText;

          // Clear existing content and rebuild properly
          roleMatchArea.innerHTML = "";

          // Create drag handle
          const dragHandle = document.createElement("span");
          dragHandle.className = "drag-handle-small";
          dragHandle.textContent = "☰";
          dragHandle.style.cssText = `
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            color: #198754;
            font-size: 1.2em;
            opacity: 0.7;
            cursor: grab;
            z-index: 2;
            pointer-events: none;
          `;

          // Create text span with proper styling
          const textSpan = document.createElement("span");
          textSpan.className = "role-text-content";
          textSpan.textContent = roleText;
          textSpan.style.cssText = `
            display: block;
            padding-left: 40px;
            padding-right: 40px;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.6;
            color: #198754;
            font-weight: 500;
            font-size: 0.95em;
            white-space: normal;
          `;

          // Append elements
          roleMatchArea.appendChild(dragHandle);
          roleMatchArea.appendChild(textSpan);

          // Set roleMatchArea styles
          roleMatchArea.style.display = "flex";
          roleMatchArea.style.alignItems = "center";
          roleMatchArea.style.position = "relative";
          roleMatchArea.style.marginTop = "0";
          roleMatchArea.style.padding = "14px 40px 14px 40px";
          roleMatchArea.style.minHeight = "60px";
          roleMatchArea.style.cursor = "grab";
          roleMatchArea.style.color = "#198754";
          roleMatchArea.style.fontStyle = "normal";
          roleMatchArea.style.fontWeight = "500";
          roleMatchArea.style.userSelect = "none";
          roleMatchArea.style.zIndex = "1";
          roleMatchArea.style.background = "#ffffff";
          roleMatchArea.style.border = "1px solid #198754";
          roleMatchArea.style.borderRadius = "6px";
          roleMatchArea.draggable = true;

          // Remove existing remove button if any
          const existingRemoveBtn = roleMatchArea.querySelector(".remove-role-btn");
          if (existingRemoveBtn) {
            existingRemoveBtn.remove();
          }

          // Add a remove button/indicator
          const removeBtn = document.createElement("span");
          removeBtn.className = "remove-role-btn";
          removeBtn.textContent = "✕";
          removeBtn.style.cssText = `
            position: absolute;
            top: 8px;
            right: 8px;
            width: 24px;
            height: 24px;
            background: #dc3545;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            cursor: pointer;
            opacity: 0.8;
            transition: opacity 0.2s;
            z-index: 10;
          `;
          removeBtn.addEventListener("mouseenter", () => {
            removeBtn.style.opacity = "1";
            removeBtn.style.background = "#c82333";
          });
          removeBtn.addEventListener("mouseleave", () => {
            removeBtn.style.opacity = "0.8";
            removeBtn.style.background = "#dc3545";
          });
          removeBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            e.preventDefault();

            // Get the role text to remove
            const roleToRemove = roleMatchArea.dataset.roleText;

            // Clear roleMatchArea
            roleMatchArea.dataset.roleText = "";
            roleMatchArea.textContent = "";
            roleMatchArea.style.display = "none";
            roleMatchArea.draggable = false;
            const dragHandle = roleMatchArea.querySelector(".drag-handle-small");
            if (dragHandle) {
              dragHandle.remove();
            }
            removeBtn.remove();

            // Show placeholder text again
            this.textContent = "பாத்திர விளக்கம் இங்கே விடவும் / Drop role here";

            // Restore the role box in roles column (remove assigned state)
            const roleBoxToShow = container.querySelector(`.level2-role-box[data-role-text="${roleToRemove}"]`);
            if (roleBoxToShow) {
              roleBoxToShow.classList.remove("assigned");
              roleBoxToShow.style.opacity = "1";
              roleBoxToShow.style.borderColor = "#667eea";
              roleBoxToShow.style.borderStyle = "solid";
              const assignedIndicator = roleBoxToShow.querySelector(".assigned-indicator");
              if (assignedIndicator) {
                assignedIndicator.remove();
              }
            }

            // Reset speaker box visual state
            this.style.borderColor = "#dee2e6";
            this.style.borderStyle = "dashed";
            this.style.background = "#f8f9fa";
            this.style.borderWidth = "2px";
            this.style.transform = "";

            // Update mapping
            updateSpeakerRoleMapping(container);

            console.log(`🗑️ Removed role "${roleToRemove}" from speaker "${this.dataset.speaker}"`);
          });
          roleMatchArea.appendChild(removeBtn);

          // Setup dragging for the matched role
          setupMatchedRoleDragging(roleMatchArea);
        }

        // Update visual state of this speaker box
        this.style.borderColor = "#198754";
        this.style.borderStyle = "solid";
        this.style.borderWidth = "2px";
        this.style.background = "#d1e7dd";
        this.style.transition = "all 0.3s ease";

        // Reset transform after drop
        setTimeout(() => {
          this.style.transform = "";
        }, 200);

        // Update speaker-to-role mapping
        updateSpeakerRoleMapping(container);

        // Log for debugging
        console.log(`✅ Matched role "${roleText}" to speaker "${speaker}"`);
      }

      const dropIndicator = this.querySelector(".drop-indicator");
      if (dropIndicator) {
        dropIndicator.style.display = "none";
      }

      return false;
    });
  });
}

// Function to reset all Level 3 answers when audio changes
function resetLevel3Answers() {
  console.log("🔄 Resetting Level 3 answers due to audio change");

  // Clear all Level 3 answer variables
  // Note: level3EmotionAnswer removed (MCQ removed)
  level3NextActionAnswer = null;
  level3MissingPhraseAnswer = null;

  // Clear level3Answers object
  level3Answers = {
    next_action: null,
    fill_missing_phrase: null,
    long_answers: {}
  };

  // Clear UI inputs for Level 3 questions (IDs 1..4)
  const level3Q1Textarea = document.getElementById("level3_q1_textarea");
  if (level3Q1Textarea) level3Q1Textarea.value = "";
  const level3Q2Input = document.getElementById("level3_q2_input");
  if (level3Q2Input) level3Q2Input.value = "";

  console.log("✅ Level 3 answers reset complete");
  console.log("   - All answer variables cleared");
  console.log("   - level3Answers object reset");
  console.log("   - UI inputs cleared");
}

// Level 3 specific question rendering
function renderLevel3Questions(questions) {
  // Safety check: Only render Level 3 questions when currentLevel === 3
  if (currentLevel !== 3) {
    console.warn("⚠️ renderLevel3Questions called but currentLevel is not 3. Skipping Level 3 rendering.");
    return;
  }

  if (!questions || !Array.isArray(questions) || questions.length === 0) {
    console.error("❌ Invalid or empty Level 3 questions array");
    el.questions.innerHTML = "<p style='color: #c0392b; padding: 20px;'>No Level 3 questions available.</p>";
    return;
  }

  // Render all Level 3 questions (MCQ removed in data)
  questions.forEach((q, idx) => {
    const displayQuestionNumber = idx + 1;

    // Q1: Short Answer – Next action (ID "1")
    if (q.id === "1" && q.type === "short_answer") {
      // Reset level3NextActionAnswer and level3Answers when rendering this question
      level3NextActionAnswer = null;
      level3Answers.next_action = null;

      const wrap = document.createElement("div");
      wrap.className = "question level3-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "short_answer";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 8px; font-weight: 500; font-size: 1.05em;";
      const marks = getQuestionMarks(3, displayQuestionNumber, q.id);
      label.innerHTML = renderQuestionText(q, displayQuestionNumber, marks);
      wrap.appendChild(label);

      // Tamil instruction text
      if (q.instruction_tamil) {
        const instruction = document.createElement("div");
        instruction.className = "tamil-instruction-text";
        instruction.style.cssText = `
          color: #6c757d;
          font-size: 0.9em;
          font-style: italic;
          margin: 4px 0 8px 0;
        `;
        instruction.textContent = q.instruction_tamil;
        wrap.appendChild(instruction);
      }

      // Answer container for positioning microphone button
      const answerContainer = document.createElement("div");
      answerContainer.style.cssText = `
        position: relative;
        margin-bottom: 12px;
      `;

      // Multiline textarea for answer
      const textarea = document.createElement("textarea");
      textarea.name = "level3_q1_short_answer";
      textarea.id = "level3_q1_textarea";
      textarea.className = "level3-short-answer-textarea";
      textarea.placeholder = "உங்கள் பதிலை இங்கே தட்டச்சு செய்யவும் / Type your answer here";
      textarea.rows = 4;
      textarea.style.cssText = `
        width: 100%;
        padding: 12px 50px 12px 12px;
        border: 2px solid #dee2e6;
        border-radius: 6px;
        font-size: 1em;
        font-family: inherit;
        resize: vertical;
        transition: border-color 0.2s;
        box-sizing: border-box;
      `;

      // Focus effect
      textarea.addEventListener("focus", () => {
        textarea.style.borderColor = "#667eea";
        textarea.style.outline = "none";
        textarea.style.boxShadow = "0 0 0 3px rgba(102, 126, 234, 0.1)";
      });

      textarea.addEventListener("blur", () => {
        textarea.style.borderColor = "#dee2e6";
        textarea.style.boxShadow = "none";
      });

      // Tamil keyboard support
      textarea.addEventListener("focus", () => {
        if (window.TamilKeyboard) {
          if (!textarea._tamilKeyboardInstance) {
            textarea._tamilKeyboardInstance = new window.TamilKeyboard(textarea);
          }
          textarea._tamilKeyboardInstance.show();
        }
      });

      // Character count indicator (optional)
      const charCount = document.createElement("div");
      charCount.className = "char-count-indicator";
      charCount.style.cssText = "margin-top: 6px; font-size: 0.85em; color: #6c757d; text-align: right;";

      const updateCharCount = () => {
        const count = textarea.value.length;
        charCount.textContent = `${count} எழுத்துகள் / ${count} characters`;
      };

      // Capture user's answer and store in level3NextActionAnswer
      // Store displayQuestionNumber in a const to ensure it's captured correctly in the closure
      const qNumber = displayQuestionNumber;
      textarea.addEventListener("input", () => {
        // Read textarea value, trim leading and trailing whitespace
        const userAnswer = textarea.value.trim();
        // Store in level3NextActionAnswer variable
        level3NextActionAnswer = userAnswer;
        // Store in level3Answers object under key "next_action"
        level3Answers.next_action = level3NextActionAnswer;
        console.log(`📝 Level 3 Q${qNumber} (next_action) answer:`, level3NextActionAnswer);
        console.log("💾 Updated level3NextActionAnswer:", level3NextActionAnswer);
        console.log("💾 Updated level3Answers.next_action:", level3Answers.next_action);
        // Auto-save to localStorage
        autoSaveAnswers();
        // Update character count
        updateCharCount();
      });

      updateCharCount(); // Initial count

      wrap.appendChild(textarea);
      wrap.appendChild(charCount);
      el.questions.appendChild(wrap);
    }

    // Q2: Fill in the missing phrase (ID "2")
    if (q.id === "2" && q.type === "fill_missing_phrase") {
      // Reset level3MissingPhraseAnswer and level3Answers when rendering this question
      level3MissingPhraseAnswer = null;
      level3Answers.fill_missing_phrase = null;

      const wrap = document.createElement("div");
      wrap.className = "question level3-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "fill_missing_phrase";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
      const marks = getQuestionMarks(3, displayQuestionNumber, q.id);
      label.innerHTML = renderQuestionText(q, displayQuestionNumber, marks);
      wrap.appendChild(label);

      // Sentence with blank display
      if (q.sentence_template) {
        const sentenceDisplay = document.createElement("div");
        sentenceDisplay.className = "sentence-with-blank";
        sentenceDisplay.style.cssText = `
          background: #f8f9fa;
          padding: 16px 20px;
          margin: 12px 0;
          border-left: 4px solid #667eea;
          border-radius: 6px;
          font-size: 1.1em;
          color: #212529;
          line-height: 1.8;
          font-weight: 500;
        `;
        sentenceDisplay.textContent = q.sentence_template;
        wrap.appendChild(sentenceDisplay);
      }

      // English reference text (read-only)
      if (q.sentence_english) {
        const englishRef = document.createElement("div");
        englishRef.className = "english-reference-text";
        englishRef.style.cssText = `
          color: #6c757d;
          font-size: 0.9em;
          font-style: italic;
          margin: 8px 0 16px 0;
          padding: 8px 12px;
          background: #f8f9fa;
          border-left: 3px solid #dee2e6;
          border-radius: 4px;
        `;
        englishRef.textContent = `(Reference: ${q.sentence_english})`;
        wrap.appendChild(englishRef);
      }

      // Single-line input for missing word / number
      const input = document.createElement("input");
      // Force text type for numeric-only so trailing dots aren't cleared by the browser
      if (q.numeric_only) {
        input.type = "text";
        input.inputMode = "decimal";
        // Allow only digits and a single dot (no commas or other chars)
        input.pattern = "^[0-9]*\\.?[0-9]*$";
      } else {
        input.type = q.input_type || "text";
      }
      input.name = "level3_q2_fill_blank";
      input.id = "level3_q2_input";
      input.className = "level3-fill-blank-input";
      input.placeholder = q.numeric_only
        ? "Enter the number"
        : "விடுபட்ட சொல்லை இங்கே தட்டச்சு செய்யவும் / Type the missing word here";
      input.style.cssText = `
        width: 100%;
        padding: 12px 16px;
        border: 2px solid #dee2e6;
        border-radius: 6px;
        font-size: 1em;
        font-family: inherit;
        transition: border-color 0.2s;
        box-sizing: border-box;
        margin-top: 12px;
      `;

      // Focus effect
      input.addEventListener("focus", () => {
        input.style.borderColor = "#667eea";
        input.style.outline = "none";
        input.style.boxShadow = "0 0 0 3px rgba(102, 126, 234, 0.1)";
      });

      input.addEventListener("blur", () => {
        input.style.borderColor = "#dee2e6";
        input.style.boxShadow = "none";
      });

      const qNumber = displayQuestionNumber;

      if (q.numeric_only) {
        input.classList.add("numeric-input"); // Mark as numeric for keyboard detection

        // Numeric hint
        const hint = document.createElement("div");
        hint.className = "question-hint";
        hint.textContent = "Numbers only (0-9 and .). Use the numeric keypad below.";
        wrap.appendChild(hint);

        // On-screen numeric keyboard (digits + dot + backspace/clear)
        const numKb = document.createElement("div");
        numKb.className = "numeric-keyboard";
        numKb.id = `numeric-kb-level3-${q.id}`; // Unique ID to prevent duplicates
        const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", ".", "⌫", "Clear"];
        keys.forEach((k) => {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "numeric-key";
          btn.textContent = k;
          numKb.appendChild(btn);
        });

        // Append input then keyboard
        wrap.appendChild(input);
        wrap.appendChild(numKb);

        // Prevent Tamil keyboard from showing for this input
        input.addEventListener("focus", (e) => {
          e.stopPropagation(); // Prevent Tamil keyboard from showing
        });

        // Normalize and store helper
        function normalizeNumeric() {
          let val = input.value.replace(/[^0-9.]/g, "");
          const parts = val.split(".");
          if (parts.length > 2) {
            val = parts.shift() + "." + parts.join("");
          }
          // If user starts with dot, normalize to 0.<rest>
          if (val.startsWith(".")) {
            val = "0" + val;
          }
          input.value = val;
          level3MissingPhraseAnswer = input.value.trim();
          level3Answers.fill_missing_phrase = level3MissingPhraseAnswer;
        }

        numKb.addEventListener("click", (e) => {
          const btn = e.target.closest(".numeric-key");
          if (!btn) return;
          const key = btn.textContent;
          if (key === "⌫") {
            input.value = input.value.slice(0, -1);
          } else if (key === "Clear") {
            input.value = "";
          } else if (key === ".") {
            // Only insert dot when tapped; ensure single dot and prefix 0 if empty
            if (input.value.includes(".")) {
              return;
            }
            if (!input.value || input.value.length === 0) {
              input.value = "0.";
            } else {
              input.value = input.value + ".";
            }
          } else {
            input.value = (input.value || "") + key;
          }
          normalizeNumeric();
          input.focus();
        });

        // Manual typing restriction
        input.addEventListener("input", normalizeNumeric);
      } else {
        // Tamil keyboard support for text input
        input.addEventListener("focus", () => {
          if (window.TamilKeyboard) {
            if (!input._tamilKeyboardInstance) {
              input._tamilKeyboardInstance = new window.TamilKeyboard(input);
            }
            input._tamilKeyboardInstance.show();
          }
        });

        input.addEventListener("input", () => {
          const userAnswer = input.value.trim().toLowerCase();
          level3MissingPhraseAnswer = userAnswer;
          level3Answers.fill_missing_phrase = level3MissingPhraseAnswer;
          console.log(`📝 Level 3 Q${qNumber} (fill_missing_phrase) answer:`, level3MissingPhraseAnswer);
          console.log("💾 Updated level3MissingPhraseAnswer:", level3MissingPhraseAnswer);
          console.log("💾 Updated level3Answers.fill_missing_phrase:", level3Answers.fill_missing_phrase);
          // Auto-save to localStorage
          autoSaveAnswers();
        });

        wrap.appendChild(input);
      }
      el.questions.appendChild(wrap);
    }

    // Long answer questions (Q4 and Q5 in internal IDs, displayed as Q3 and Q4 in UI)
    if (q.type === "long_answer") {
      // Initialize long_answers object if needed
      if (!level3Answers.long_answers) {
        level3Answers.long_answers = {};
      }
      // Reset this specific long answer when rendering
      level3Answers.long_answers[q.id] = null;

      const wrap = document.createElement("div");
      wrap.className = "question level3-question";
      wrap.dataset.questionId = q.id;
      wrap.dataset.questionType = "long_answer";

      // Question label with Tamil text (bold) and English translation (italic/muted)
      const label = document.createElement("label");
      label.className = "question-label";
      label.style.cssText = "display: block; margin-bottom: 12px; font-weight: 500; font-size: 1.05em;";
      const marks = getQuestionMarks(3, displayQuestionNumber, q.id);
      label.innerHTML = renderQuestionText(q, displayQuestionNumber, marks);
      wrap.appendChild(label);

      // Tamil instruction text
      if (q.instruction_tamil) {
        const instruction = document.createElement("div");
        instruction.className = "tamil-instruction-text";
        instruction.style.cssText = `
          color: #6c757d;
          font-size: 0.9em;
          font-style: italic;
          margin: 4px 0 8px 0;
        `;
        instruction.textContent = q.instruction_tamil;
        wrap.appendChild(instruction);
      }

      // Answer container for positioning microphone button
      const answerContainer = document.createElement("div");
      answerContainer.style.cssText = `
        position: relative;
        margin-bottom: 12px;
      `;

      // Large textarea for long answer
      const textarea = document.createElement("textarea");
      textarea.name = `level3_q${q.id}_long_answer`;
      textarea.id = `level3_q${q.id}_textarea`;
      textarea.className = "level3-long-answer-textarea";
      textarea.placeholder = "உங்கள் பதிலை இங்கே தட்டச்சு செய்யவும் / Type your answer here";
      textarea.rows = 8;
      textarea.style.cssText = `
        width: 100%;
        padding: 12px 50px 12px 12px;
        border: 2px solid #dee2e6;
        border-radius: 6px;
        font-size: 1em;
        font-family: inherit;
        resize: vertical;
        transition: border-color 0.2s;
        box-sizing: border-box;
        min-height: 150px;
      `;

      // Focus effect
      textarea.addEventListener("focus", () => {
        textarea.style.borderColor = "#667eea";
        textarea.style.outline = "none";
        textarea.style.boxShadow = "0 0 0 3px rgba(102, 126, 234, 0.1)";
      });

      textarea.addEventListener("blur", () => {
        textarea.style.borderColor = "#dee2e6";
        textarea.style.boxShadow = "none";
      });

      // Tamil keyboard support
      textarea.addEventListener("focus", () => {
        if (window.TamilKeyboard) {
          if (!textarea._tamilKeyboardInstance) {
            textarea._tamilKeyboardInstance = new window.TamilKeyboard(textarea);
          }
          textarea._tamilKeyboardInstance.show();
        }
      });

      // Character count indicator
      const charCount = document.createElement("div");
      charCount.className = "char-count-indicator";
      charCount.style.cssText = "margin-top: 6px; font-size: 0.85em; color: #6c757d; text-align: right;";

      const updateCharCount = () => {
        const count = textarea.value.length;
        charCount.textContent = `${count} எழுத்துகள் / ${count} characters`;
      };

      // Capture user's answer and store in level3Answers by question ID
      // Store displayQuestionNumber in a const to ensure it's captured correctly in the closure
      const qNumber = displayQuestionNumber;
      textarea.addEventListener("input", () => {
        // Read textarea value, trim leading and trailing whitespace
        const userAnswer = textarea.value.trim();
        // Store in level3Answers.long_answers object keyed by question ID
        level3Answers.long_answers[q.id] = userAnswer;
        console.log(`📝 Level 3 Q${qNumber} (long_answer, internal ID ${q.id}):`, userAnswer);
        console.log(`💾 Updated level3Answers.long_answers[${q.id}]:`, level3Answers.long_answers[q.id]);
        // Auto-save to localStorage
        autoSaveAnswers();
        // Update character count
        updateCharCount();
      });

      updateCharCount(); // Initial count

      answerContainer.appendChild(textarea);

      // Microphone is available in the keyboard - no need for separate mic button in answer box
      wrap.appendChild(answerContainer);
      wrap.appendChild(charCount);
      el.questions.appendChild(wrap);
    }

  });
}

// Level 2 specific drag and drop handler for dialogue ordering
function initLevel2DragAndDrop(container) {
  // Safety check: Only initialize Level 2 drag-and-drop when currentLevel === 2
  if (currentLevel !== 2) {
    console.warn("⚠️ initLevel2DragAndDrop called but currentLevel is not 2. Skipping initialization.");
    return;
  }

  let draggedElement = null;

  // Get all draggable items
  const items = container.querySelectorAll(".level2-ordering-item");

  items.forEach((item) => {
    // Ensure draggable attribute is set
    item.setAttribute("draggable", "true");

    // Drag start: Initialize drag operation
    item.addEventListener("dragstart", function (e) {
      draggedElement = this;
      this.classList.add("dragging");
      this.style.opacity = "0.5";
      this.style.borderColor = "#667eea";
      this.style.transform = "rotate(2deg)";

      // Set drag data
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", this.dataset.itemId || "");

      // Add visual feedback
      this.style.cursor = "grabbing";
    });

    // Drag end: Clean up after drag operation
    item.addEventListener("dragend", function () {
      this.classList.remove("dragging");
      this.style.opacity = "1";
      this.style.transform = "none";
      this.style.cursor = "move";

      // Reset all items' visual states
      container.querySelectorAll(".level2-ordering-item").forEach(i => {
        i.classList.remove("drag-over");
        if (!i.classList.contains("dragging")) {
          i.style.borderColor = "#dee2e6";
          i.style.boxShadow = "none";
          i.style.backgroundColor = "#ffffff";
        }
      });

      draggedElement = null;
    });

    // Drag over: Allow drop and show visual feedback
    item.addEventListener("dragover", function (e) {
      e.preventDefault(); // Required to allow drop
      e.stopPropagation();

      if (draggedElement && draggedElement !== this) {
        e.dataTransfer.dropEffect = "move";

        // Add visual feedback for drop target
        this.classList.add("drag-over");
        this.style.borderColor = "#198754";
        this.style.backgroundColor = "#f0f9ff";
        this.style.borderWidth = "2px";
        this.style.borderStyle = "dashed";
      }

      return false;
    });

    // Drag leave: Remove visual feedback when leaving drop target
    item.addEventListener("dragleave", function () {
      this.classList.remove("drag-over");
      if (!this.classList.contains("dragging")) {
        this.style.borderColor = "#dee2e6";
        this.style.backgroundColor = "#ffffff";
        this.style.borderWidth = "2px";
        this.style.borderStyle = "solid";
      }
    });

    // Drop: Handle the drop and reorder items
    item.addEventListener("drop", function (e) {
      e.preventDefault();
      e.stopPropagation();

      if (draggedElement && draggedElement !== this) {
        // Get current order of all items
        const allItems = Array.from(container.querySelectorAll(".level2-ordering-item"));
        const draggedIndex = allItems.indexOf(draggedElement);
        const targetIndex = allItems.indexOf(this);

        // Reorder in DOM: Insert dragged element before or after target
        if (draggedIndex < targetIndex) {
          // Moving down: Insert after target
          container.insertBefore(draggedElement, this.nextSibling);
        } else {
          // Moving up: Insert before target
          container.insertBefore(draggedElement, this);
        }

        // Log the new order for debugging
        const newOrder = Array.from(container.querySelectorAll(".level2-ordering-item"))
          .map(i => parseInt(i.dataset.itemId, 10))
          .filter(id => !isNaN(id));
        console.log("📋 New dialogue order:", newOrder);

        // Store in level2Answers object
        if (newOrder.length > 0) {
          level2Answers.dialogue_ordering = newOrder;
          console.log("💾 Updated level2Answers.dialogue_ordering:", level2Answers.dialogue_ordering);
          // Auto-save to localStorage
          autoSaveAnswers();
        }
      }

      // Clean up visual state
      this.classList.remove("drag-over");
      this.style.borderColor = "#dee2e6";
      this.style.backgroundColor = "#ffffff";
      this.style.borderWidth = "2px";
      this.style.borderStyle = "solid";

      return false;
    });
  });

  console.log(`✅ Drag-and-drop initialized for ${items.length} dialogue items`);
}

async function fetchJson(url, options = {}, timeout = 120000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    // Ensure URL is properly formatted
    const fullUrl = url.startsWith('http') ? url : (url.startsWith('/') ? url : '/' + url);
    console.log(`[fetchJson] Fetching: ${fullUrl}`);

    const res = await fetch(fullUrl, {
      ...options,
      signal: controller.signal,
      credentials: 'same-origin', // Include cookies for same-origin requests
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const text = await res.text();
      console.error(`[fetchJson] HTTP ${res.status} error:`, text);
      let errorMessage = `HTTP ${res.status}`;
      try {
        const errorData = JSON.parse(text);
        errorMessage = errorData.error || errorData.message || errorMessage;
      } catch (e) {
        errorMessage = text.substring(0, 100) || errorMessage;
      }
      throw new Error(errorMessage);
    }

    const data = await res.json();
    console.log(`[fetchJson] Success: ${fullUrl}`, data);
    return data;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      console.error(`[fetchJson] Timeout: ${url}`);
      throw new Error(`Request timeout after ${timeout}ms. The server may be slow or unresponsive.`);
    }
    if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
      console.error(`[fetchJson] Network error: ${url}`, err);
      throw new Error(`Cannot connect to server. Please make sure the Flask server is running (python Backend/app.py).`);
    }
    console.error(`[fetchJson] Error: ${url}`, err);
    throw err;
  }
}

async function loadLevel(level) {
  console.log(`🔄 Loading level ${level}...`);
  console.log(`⏰ Time: ${new Date().toISOString()}`);

  // Verify elements are available
  if (!el.audioStatus || !el.questions) {
    console.error("❌ Elements not initialized!");
    initializeElements();
    if (!el.audioStatus || !el.questions) {
      console.error("❌ Still missing elements after re-initialization!");
      return;
    }
  }

  currentLevel = level;
  setActive(level);

  // Reset UI
  msg(el.audioStatus, "Loading...", "#667eea");
  if (el.questions) {
    el.questions.innerHTML = "<p style='color: #667eea; padding: 20px; text-align: center;'>Loading questions... / கேள்விகளை ஏற்றுகிறது...</p>";
  }
  if (el.resultCard) {
    el.resultCard.style.display = "none";
  }

  try {
    const apiUrl = `${API_BASE_URL}/api/start-test/${level}`;
    console.log(`📡 Fetching: ${apiUrl}`);

    const startData = await fetchJson(apiUrl);
    console.log("✅ Start data received:", startData);
    console.log("📊 Data structure:", {
      hasAudio: !!startData.audio,
      hasQuestions: !!startData.questions,
      questionsIsArray: Array.isArray(startData.questions),
      questionsLength: startData.questions ? startData.questions.length : 0
    });

    // Get audio_id from response
    let audioId = null;
    if (startData.audio && startData.audio.audio_id) {
      audioId = startData.audio.audio_id;
    } else {
      // Fallback to default mapping
      audioId = levelAudioMap[level] || `level${level}_classroom_tamil`;
      console.warn(`Audio ID not found in response, using fallback: ${audioId}`);
    }

    // For Level 2, ensure we use level2.mp4 file
    if (level === 2) {
      audioId = "level2";
      console.log("🎵 Level 2: Using level2.mp4 file");
    }

    if (!audioId) {
      throw new Error("Could not determine audio ID for this level");
    }

    currentAudioId = audioId;

    // Ensure native controls are enabled (standard HTML5 audio player)
    el.audioPlayer.controls = true;
    // Prevent download and pause - only allow play
    el.audioPlayer.setAttribute('controlsList', 'nodownload nopause');

    // Initialize play count for this level
    audioPlayCountKey = `audio_play_count_level_${level}`;
    audioPlayCount = parseInt(localStorage.getItem(audioPlayCountKey) || '0', 10);
    console.log(`🎵 Audio play count for level ${level}: ${audioPlayCount}`);

    // Hide custom play button - use native controls only
    if (el.playAudioBtn) {
      el.playAudioBtn.style.display = "none";
      el.playAudioBtn.style.visibility = "hidden";
    }
    if (el.playInstruction) {
      el.playInstruction.style.display = "none";
      el.playInstruction.style.visibility = "hidden";
    }

    // Load audio
    const audioUrl = startData.audio?.url || `/audio/${audioId}`;
    console.log(`🎵 Loading audio from: ${audioUrl}`);

    msg(el.audioStatus, "Loading audio... / ஆடியோவை ஏற்றுகிறது...", "#667eea");

    // Set up audio event handlers
    el.audioPlayer.onloadstart = () => {
      msg(el.audioStatus, "Loading audio... / ஆடியோவை ஏற்றுகிறது...", "#667eea");
    };

    el.audioPlayer.onloadeddata = () => {
      console.log("✅ Audio loaded successfully");
      // For Level 3, ensure playback position is reset to start
      if (level === 3) {
        el.audioPlayer.currentTime = 0;
        console.log("✅ Level 3 audio reset to start position");
      }
      msg(el.audioStatus, "Audio ready / ஆடியோ தயார்", "#198754");

    };

    el.audioPlayer.oncanplay = () => {
      console.log("✅ Audio can play");
      msg(el.audioStatus, "Audio ready / ஆடியோ தயார்", "#198754");

    };

    el.audioPlayer.onerror = (e) => {
      console.error("❌ Audio loading error:", e, el.audioPlayer.error);
      msg(el.audioStatus, "❌ ஆடியோவை ஏற்ற முடியவில்லை", "#c0392b");
    };

    // Track audio play count (max 2 plays) and ensure it plays fully
    let isCurrentlyPlaying = false;
    let playbackMonitor = null;
    let hasStartedPlay = false; // Track if a play has started (to count plays)

    // Reset audio to beginning when starting a new play
    el.audioPlayer.onplay = () => {
      // Check if already played 2 times
      if (audioPlayCount >= 2) {
        console.log("🚫 Audio limit reached (2 plays)");
        el.audioPlayer.pause();
        el.audioPlayer.currentTime = 0;
        isCurrentlyPlaying = false;
        hasStartedPlay = false;
        msg(el.audioStatus, "Audio limit reached (2 plays) / ஆடியோ வரம்பு (2 முறை)", "#ffc107");
        return;
      }

      // If this is a new play (not resuming from pause), increment count and reset to beginning
      if (!hasStartedPlay) {
        audioPlayCount++;
        localStorage.setItem(audioPlayCountKey, audioPlayCount.toString());
        console.log(`🎵 Audio play #${audioPlayCount} for level ${level} - starting from beginning`);
        hasStartedPlay = true;
      }

      // Always ensure audio starts from beginning when play starts
      if (el.audioPlayer.currentTime > 0 && !isCurrentlyPlaying) {
        el.audioPlayer.currentTime = 0;
      }

      isCurrentlyPlaying = true;

      // Clear any existing monitor
      if (playbackMonitor) {
        clearInterval(playbackMonitor);
      }

      // Monitor playback state - ensure it plays fully
      playbackMonitor = setInterval(() => {
        if (isCurrentlyPlaying && el.audioPlayer.paused && !el.audioPlayer.ended) {
          // If paused, reset to beginning
          el.audioPlayer.currentTime = 0;
          hasStartedPlay = false; // Reset flag so next play counts as new
          isCurrentlyPlaying = false;
          console.log("⏸️ Pause detected - reset to beginning");
        }
        if (el.audioPlayer.ended) {
          clearInterval(playbackMonitor);
          playbackMonitor = null;
          isCurrentlyPlaying = false;
          hasStartedPlay = false; // Reset for next play

          if (audioPlayCount >= 2) {
            // Disable audio after 2 plays
            el.audioPlayer.controls = false;
            el.audioPlayer.style.pointerEvents = 'none';
            msg(el.audioStatus, "Audio limit reached (2 plays) / ஆடியோ வரம்பு (2 முறை)", "#ffc107");
          }
        }
      }, 100);

      if (audioPlayCount >= 2) {
        // Disable audio after 2 plays when it ends
        el.audioPlayer.onended = () => {
          isCurrentlyPlaying = false;
          hasStartedPlay = false;
          if (playbackMonitor) {
            clearInterval(playbackMonitor);
            playbackMonitor = null;
          }
          el.audioPlayer.controls = false;
          el.audioPlayer.style.pointerEvents = 'none';
          msg(el.audioStatus, "Audio limit reached (2 plays) / ஆடியோ வரம்பு (2 முறை)", "#ffc107");
        };
      } else {
        // Reset playing state when audio ends normally
        el.audioPlayer.onended = () => {
          isCurrentlyPlaying = false;
          hasStartedPlay = false;
          if (playbackMonitor) {
            clearInterval(playbackMonitor);
            playbackMonitor = null;
          }
          console.log(`✅ Audio play #${audioPlayCount} completed fully`);
        };
      }
    };

    // Handle pause - reset to beginning
    el.audioPlayer.addEventListener('pause', () => {
      if (isCurrentlyPlaying && !el.audioPlayer.ended) {
        console.log("⏸️ Pause detected - resetting to beginning");
        el.audioPlayer.currentTime = 0;
        hasStartedPlay = false; // Reset flag so next play counts as new play
        isCurrentlyPlaying = false;
      }
    });

    // Prevent seeking while playing - reset to beginning
    el.audioPlayer.addEventListener('seeking', () => {
      if (isCurrentlyPlaying && !el.audioPlayer.ended) {
        console.log("⏩ Seeking detected - resetting to beginning");
        el.audioPlayer.currentTime = 0;
      }
    });

    // Ensure audio always starts from beginning when loaded
    el.audioPlayer.onloadeddata = () => {
      el.audioPlayer.currentTime = 0;
      hasStartedPlay = false;
    };

    // Check if play count already reached
    if (audioPlayCount >= 2) {
      el.audioPlayer.controls = false;
      el.audioPlayer.style.pointerEvents = 'none';
      msg(el.audioStatus, "Audio limit reached (2 plays) / ஆடியோ வரம்பு (2 முறை)", "#ffc107");
    }

    // Clear any previous audio source to prevent duplicate loading
    // This ensures only one audio element is active at a time
    // Prevents references to previous Level 3 audio files or any other audio sources
    if (el.audioPlayer.src) {
      console.log("🔄 Clearing previous audio source before loading new one");
      el.audioPlayer.src = "";
      el.audioPlayer.load(); // Clear the previous source
    }

    // For Level 3, ensure we're using the correct audio source only
    // No fallback or duplicate audio sources should exist
    if (level === 3) {
      console.log("🎵 Level 3 selected: Loading audio automatically and resetting playback position to start");

      // Always reset Level 3 answers when Level 3 audio is loaded
      // This prevents answers from previous audio being reused
      // Reset happens before setting new audio source to ensure clean state
      resetLevel3Answers();

      // Double-check: ensure no previous audio source remains
      if (el.audioPlayer.src) {
        console.log("⚠️ Additional cleanup: Clearing any remaining audio source for Level 3");
        el.audioPlayer.src = "";
        el.audioPlayer.load();
      }
    }

    // Set source and load (only one active audio element)
    el.audioPlayer.src = audioUrl;

    // Always show the audio element with standard HTML5 controls
    el.audioPlayer.style.display = "block";
    el.audioPlayer.style.visibility = "visible";
    el.audioPlayer.style.width = "100%";
    el.audioPlayer.style.maxWidth = "480px";
    el.audioPlayer.style.marginTop = "10px";
    el.audioPlayer.style.marginBottom = "10px";

    // Ensure native browser controls are enabled (standard HTML5 audio player)
    el.audioPlayer.controls = true;
    // Ensure audio is not muted
    el.audioPlayer.muted = false;
    // Prevent download and pause - only allow play
    el.audioPlayer.setAttribute('controlsList', 'nodownload nopause');

    // Initialize play count for this level
    audioPlayCountKey = `audio_play_count_level_${level}`;
    audioPlayCount = parseInt(localStorage.getItem(audioPlayCountKey) || '0', 10);
    console.log(`🎵 Audio play count for level ${level}: ${audioPlayCount}`);

    // Hide custom play button - use native controls only
    if (el.playAudioBtn) {
      el.playAudioBtn.style.display = "none";
      el.playAudioBtn.style.visibility = "hidden";
    }
    if (el.playInstruction) {
      el.playInstruction.style.display = "none";
      el.playInstruction.style.visibility = "hidden";
    }


    // Temporary debug log: Confirm Level 3 audio is loaded
    if (level === 3) {
      console.log("🔍 [DEBUG] Level 3 audio file path:", audioUrl);
      console.log("🔍 [DEBUG] Level 3 audio ID:", audioId);
      console.log("🔍 [DEBUG] Full audio source URL:", el.audioPlayer.src);
    }

    // Reset playback position to start for all levels
    el.audioPlayer.currentTime = 0;
    el.audioPlayer.pause(); // Ensure audio is paused at start

    // For Level 3, ensure audio loads automatically and resets to start
    if (level === 3) {
      el.audioPlayer.currentTime = 0;
      el.audioPlayer.pause();
    }

    // Load the audio (this triggers loading but doesn't preload for other levels)
    // Audio only loads when loadLevel is called, not preloaded
    // Only one audio source is active at a time
    el.audioPlayer.load();

    // Load questions directly from API response
    let questions = [];

    if (startData.questions && Array.isArray(startData.questions)) {
      questions = startData.questions;
      console.log(`✅ Loaded ${questions.length} questions from API response`);
    } else if (startData.questions) {
      // If questions is an object, extract the array
      questions = normalizeQuestions(startData.questions);
      console.log(`✅ Extracted ${questions.length} questions from response object`);
    } else {
      // Fallback: fetch separately
      console.log(`⚠️ No questions in response, fetching from /questions/${audioId}...`);
      try {
        const questionsResponse = await fetchJson(`/questions/${audioId}`);
        questions = normalizeQuestions(questionsResponse);
        console.log(`✅ Loaded ${questions.length} questions from separate endpoint`);
      } catch (err) {
        console.error("❌ Failed to fetch questions:", err);
        throw new Error(`Could not load questions: ${err.message}`);
      }
    }

    // Validate questions
    if (!questions || questions.length === 0) {
      throw new Error("No questions found. Please check the server configuration.");
    }

    // Render questions immediately
    console.log(`🎨 Rendering ${questions.length} questions...`);
    if (el.questions) {
      el.questions.innerHTML = ""; // Clear loading message
    }
    renderQuestions(questions);

    // Restore saved answers if they exist (persist across navigation)
    const savedAnswersKey = `level_${level}_answers`;
    const savedAnswers = localStorage.getItem(savedAnswersKey);
    if (savedAnswers) {
      try {
        const parsedAnswers = JSON.parse(savedAnswers);
        console.log(`📝 Restoring saved answers for Level ${level}:`, parsedAnswers);
        // Wait for DOM to be ready, then restore
        // Use requestAnimationFrame to ensure DOM is fully rendered
        requestAnimationFrame(() => {
          setTimeout(() => {
            restoreAnswers(level, parsedAnswers, questions);
            console.log(`✅ Answers restored for Level ${level}`);
            // Also restore Level 2 dialogue ordering if needed (after a bit more delay)
            if (level === 2 && parsedAnswers.level2Answers && parsedAnswers.level2Answers.dialogue_ordering) {
              setTimeout(() => {
                const q2Element = document.querySelector('.level2-question[data-question-id="2"]');
                if (q2Element) {
                  const orderingList = q2Element.querySelector('.dialogue-ordering-list');
                  if (orderingList) {
                    const items = Array.from(orderingList.querySelectorAll('.level2-ordering-item'));
                    const savedOrder = parsedAnswers.level2Answers.dialogue_ordering;
                    items.sort((a, b) => {
                      const aId = parseInt(a.dataset.itemId, 10);
                      const bId = parseInt(b.dataset.itemId, 10);
                      const aIndex = savedOrder.indexOf(aId);
                      const bIndex = savedOrder.indexOf(bId);
                      return aIndex - bIndex;
                    });
                    items.forEach(item => orderingList.appendChild(item));
                    console.log("✅ Restored dialogue ordering:", savedOrder);
                  }
                }
              }, 200);
            }
          }, 300);
        });
      } catch (err) {
        console.error(`❌ Error restoring answers for Level ${level}:`, err);
      }
    } else {
      console.log(`✅ Level ${level} loaded (no previous answers to restore)`);
    }

    // Update submit button text based on level
    if (el.submitBtn) {
      if (level < 3) {
        el.submitBtn.textContent = "Next Level →";
      } else {
        el.submitBtn.textContent = "Submit Answers";
      }
    }

    // Verify rendering
    const renderedCount = el.questions ? el.questions.querySelectorAll(".question").length : 0;
    if (renderedCount === 0) {
      throw new Error("Failed to render questions. Check console for details.");
    }

    console.log(`✅ Successfully loaded and rendered ${renderedCount} questions!`);
  } catch (err) {
    console.error("❌ Load level error:", err);
    console.error("Error details:", err.stack);
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);

    if (el.audioStatus) {
      msg(el.audioStatus, `❌ Error: ${err.message}`, "#c0392b");
    }
    if (el.questions) {
      el.questions.innerHTML =
        `<div style='color:#c0392b; padding: 20px; border: 2px solid #c0392b; border-radius: 8px; background: #ffe6e6;'>
          <strong style='font-size: 1.1em;'>⚠️ Error loading content:</strong><br><br>
          <code style='background: white; padding: 5px; border-radius: 4px;'>${err.message}</code><br><br>
          <small>Please check the browser console (F12) for more details.</small><br>
          <button onclick='location.reload()' style='margin-top: 10px; padding: 8px 16px; background: #c0392b; color: white; border: none; border-radius: 4px; cursor: pointer;'>Reload Page</button>
        </div>`;
    }
  }
}

// Function to auto-save answers to localStorage
function autoSaveAnswers() {
  try {
    if (currentLevel === 1) {
      const responses = collectResponses();
      localStorage.setItem(`level_${currentLevel}_answers`, JSON.stringify(responses));
      console.log(`💾 Auto-saved Level ${currentLevel} answers`);
    } else if (currentLevel === 2) {
      const responses = collectResponses();
      localStorage.setItem(`level_${currentLevel}_answers`, JSON.stringify(responses));
      console.log(`💾 Auto-saved Level ${currentLevel} answers`);
    } else if (currentLevel === 3) {
      const responses = collectResponses();
      localStorage.setItem(`level_${currentLevel}_answers`, JSON.stringify(responses));
      console.log(`💾 Auto-saved Level ${currentLevel} answers`);
    }
  } catch (err) {
    console.error("Error auto-saving answers:", err);
  }
}

// Function to restore saved answers to the UI
function restoreAnswers(level, savedAnswers, questions) {
  if (level === 1) {
    // Restore Level 1 answers
    questions.forEach((q) => {
      const questionElement = document.querySelector(`.question[data-question-id="${q.id}"]`);
      if (!questionElement) return;

      const answer = savedAnswers[q.id];
      if (answer !== null && answer !== undefined && answer !== '') {
        // Handle MCQ
        const radios = questionElement.querySelectorAll('input[type="radio"]');
        if (radios.length > 0) {
          radios.forEach(radio => {
            if (radio.value === answer) {
              radio.checked = true;
            }
          });
        } else {
          // Check if it's an ordering question
          const orderingContainer = questionElement.querySelector('.ordering-container');
          if (orderingContainer && typeof answer === 'string') {
            // Restore ordering: answer is comma-separated values
            const order = answer.split(',').map(v => v.trim()).filter(v => v);
            const listContainer = orderingContainer.querySelector('.ordering-list');
            if (listContainer && order.length > 0) {
              const items = Array.from(listContainer.querySelectorAll('.ordering-item'));
              // Sort items according to saved order
              items.sort((a, b) => {
                const aValue = a.dataset.value;
                const bValue = b.dataset.value;
                const aIndex = order.indexOf(aValue);
                const bIndex = order.indexOf(bValue);
                return aIndex - bIndex;
              });
              // Re-append items in correct order
              items.forEach(item => listContainer.appendChild(item));
              console.log(`✅ Restored Level 1 Q${q.id} ordering:`, order);
            }
          } else {
            // Handle text input
            const input = questionElement.querySelector('input, textarea');
            if (input) {
              input.value = answer;
            }
          }
        }
      }
    });
  } else if (level === 2) {
    // Restore Level 2 answers
    const level2Answers = savedAnswers.level2Answers || {};

    // Q1: identify_speaker (MCQ)
    if (level2Answers.identify_speaker) {
      const q1Element = document.querySelector('.level2-question[data-question-id="1"]');
      if (q1Element) {
        const radios = q1Element.querySelectorAll('input[type="radio"]');
        radios.forEach(radio => {
          if (radio.value === level2Answers.identify_speaker) {
            radio.checked = true;
          }
        });
      }
    }

    // Q2: dialogue_ordering (drag and drop)
    if (level2Answers.dialogue_ordering && Array.isArray(level2Answers.dialogue_ordering)) {
      const q2Element = document.querySelector('.level2-question[data-question-id="2"]');
      if (q2Element) {
        const orderingList = q2Element.querySelector('.dialogue-ordering-list');
        if (orderingList) {
          // Reorder items based on saved order
          const items = Array.from(orderingList.querySelectorAll('.level2-ordering-item'));
          const savedOrder = level2Answers.dialogue_ordering;

          // Sort items according to saved order
          items.sort((a, b) => {
            const aId = parseInt(a.dataset.itemId, 10);
            const bId = parseInt(b.dataset.itemId, 10);
            const aIndex = savedOrder.indexOf(aId);
            const bIndex = savedOrder.indexOf(bId);
            return aIndex - bIndex;
          });

          // Re-append items in correct order
          items.forEach(item => orderingList.appendChild(item));
          console.log("✅ Restored dialogue ordering:", savedOrder);
        }
      }
    }

    // Q3: main_problem_discussed (textarea)
    if (level2Answers.main_problem_discussed) {
      const q3Element = document.querySelector('.level2-question[data-question-id="3"]');
      if (q3Element) {
        const textarea = q3Element.querySelector('textarea');
        if (textarea) {
          textarea.value = level2Answers.main_problem_discussed;
        }
      }
    }

    // Q4: match_speaker_role (dropdowns)
    if (level2Answers.match_speaker_role && typeof level2Answers.match_speaker_role === 'object') {
      const q4Element = document.querySelector('.level2-question[data-question-id="4"]');
      if (q4Element) {
        const selects = q4Element.querySelectorAll('.speaker-role-select');
        selects.forEach(select => {
          const speaker = select.dataset.speaker;
          const role = level2Answers.match_speaker_role[speaker];
          if (role) {
            select.value = role;
          }
        });
      }
    }
  } else if (level === 3) {
    // Restore Level 3 answers
    const level3Answers = savedAnswers.level3Answers || {};

    // Q1: next_action
    if (level3Answers.next_action) {
      const q1Element = document.querySelector('.level3-question[data-question-id="1"]');
      if (q1Element) {
        const textarea = q1Element.querySelector('.level3-short-answer-textarea');
        if (textarea) {
          textarea.value = level3Answers.next_action;
        }
      }
    }

    // Q2: fill_missing_phrase
    if (level3Answers.fill_missing_phrase) {
      const q2Element = document.querySelector('.level3-question[data-question-id="2"]');
      if (q2Element) {
        const input = q2Element.querySelector('input');
        if (input) {
          input.value = level3Answers.fill_missing_phrase;
        }
      }
    }

    // Q3, Q4: long_answers
    if (level3Answers.long_answers) {
      const longAnswers = level3Answers.long_answers;
      if (longAnswers["3"]) {
        const q3Element = document.querySelector('.level3-question[data-question-id="3"]');
        if (q3Element) {
          const textarea = q3Element.querySelector('.level3-long-answer-textarea');
          if (textarea) {
            textarea.value = longAnswers["3"];
          }
        }
      }
      if (longAnswers["4"]) {
        const q4Element = document.querySelector('.level3-question[data-question-id="4"]');
        if (q4Element) {
          const textarea = q4Element.querySelector('.level3-long-answer-textarea');
          if (textarea) {
            textarea.value = longAnswers["4"];
          }
        }
      }
    }
  }
}

function collectResponses() {
  const responses = {};

  // Level 2 specific response collection
  if (currentLevel === 2) {
    const level2Answers = {
      identify_speaker: null,
      dialogue_ordering: null,
      main_problem_discussed: null,
      match_speaker_role: null,
      long_answers: {}
    };

    // Question 1: MCQ - store under identify_speaker
    const level2Q1 = document.querySelector('.level2-question[data-question-id="1"]');
    if (level2Q1) {
      const checkedRadio = level2Q1.querySelector('input[type="radio"]:checked');
      if (checkedRadio) {
        level2Answers.identify_speaker = checkedRadio.value.trim();
      }
    }

    // Question 2: Dialogue Ordering - capture final order as array of data-id values
    const level2Q2 = document.querySelector('.level2-question[data-question-id="2"]');
    if (level2Q2) {
      const orderingList = level2Q2.querySelector('.dialogue-ordering-list');
      if (orderingList) {
        // Get all items in their current DOM order (after reordering)
        const items = orderingList.querySelectorAll('.level2-ordering-item');

        // Read data-id values and convert to numbers
        const dialogueOrderAnswer = Array.from(items).map(item => {
          const itemId = item.dataset.itemId;
          // Convert to number if it's a valid number string, otherwise keep as string
          return itemId ? parseInt(itemId, 10) : null;
        }).filter(id => id !== null); // Remove any null values

        if (dialogueOrderAnswer.length > 0) {
          // Store dialogue ordering answer in level2Answers object under key "dialogue_ordering"
          // Example: level2Answers.dialogue_ordering = [3, 2, 4, 1, 5, 6]
          level2Answers.dialogue_ordering = dialogueOrderAnswer;

          // Log for debugging
          console.log("📋 Captured dialogue order:", dialogueOrderAnswer);
          console.log("💾 Stored in level2Answers.dialogue_ordering:", level2Answers.dialogue_ordering);
        }
      }
    }

    // Question 3: Short Answer - capture user's answer
    const level2Q3 = document.querySelector('.level2-question[data-question-id="3"]');
    if (level2Q3) {
      const textarea = level2Q3.querySelector('.level2-short-answer-textarea');
      if (textarea) {
        // Read the value from the textarea and trim leading/trailing whitespace
        const mainProblemAnswer = textarea.value.trim();

        // Store main problem answer in level2Answers object under key "main_problem_discussed"
        // Example: level2Answers.main_problem_discussed = mainProblemAnswer
        level2Answers.main_problem_discussed = mainProblemAnswer;

        // Log for debugging
        console.log("📝 Captured main problem answer:", mainProblemAnswer);
        console.log("💾 Stored in level2Answers.main_problem_discussed:", level2Answers.main_problem_discussed);
      }
    }

    // Question 4: Match Speaker Role - store under match_speaker_role as object
    const level2Q4 = document.querySelector('.level2-question[data-question-id="4"]');
    if (level2Q4) {
      const matchingContainer = level2Q4.querySelector('.speaker-role-matching-container');
      if (matchingContainer) {
        // Check if using dropdown/select interface (new method)
        const selects = matchingContainer.querySelectorAll('.speaker-role-select');
        if (selects.length > 0) {
          // Using dropdown/select interface
          const matchMapping = {};
          selects.forEach(select => {
            const speaker = select.dataset.speaker;
            const selectedRole = select.value;
            if (selectedRole && selectedRole.trim() !== "") {
              matchMapping[speaker] = selectedRole.trim();
            }
          });
          if (Object.keys(matchMapping).length > 0) {
            level2Answers.match_speaker_role = matchMapping;
          }
        } else {
          // Legacy drag-and-drop interface
          const speakerBoxes = matchingContainer.querySelectorAll('.speaker-box');
          const matchMapping = {};

          speakerBoxes.forEach(speakerBox => {
            const speaker = speakerBox.dataset.speaker;
            const roleMatchArea = speakerBox.querySelector('.role-match-area[data-role-text]');

            // Check if roleMatchArea exists and has a non-empty roleText
            if (roleMatchArea && roleMatchArea.dataset.roleText && roleMatchArea.dataset.roleText.trim() !== "") {
              const roleText = roleMatchArea.dataset.roleText.trim();
              matchMapping[speaker] = roleText;
            }
          });

          if (Object.keys(matchMapping).length > 0) {
            level2Answers.match_speaker_role = matchMapping;
          }
        }
      }
    }

    // Question 5: Long Answer - REMOVED (Level 2 now only has Q1-Q4)
    /*
    const level2LongAnswerQuestions = document.querySelectorAll('.level2-question[data-question-type="long_answer"]');
    level2LongAnswerQuestions.forEach(qElement => {
      const questionId = qElement.dataset.questionId;
      const textarea = qElement.querySelector('textarea.level2-long-answer-textarea');
      if (textarea && questionId) {
        const userAnswer = textarea.value.trim();
        if (userAnswer) {
          level2Answers.long_answers[questionId] = userAnswer;
          console.log(`📝 Collected Level 2 Long Answer Q${questionId}:`, userAnswer);
        }
      }
    });
    */

    // Fallback: Also use global level2Answers.long_answers if DOM collection didn't find values
    // Use the global level2Answers object (defined at top of file) as fallback
    if (typeof window !== 'undefined' && typeof window.level2Answers !== 'undefined' && window.level2Answers.long_answers) {
      Object.keys(window.level2Answers.long_answers).forEach(qId => {
        // Only add if not already collected from DOM
        if (!level2Answers.long_answers[qId] && window.level2Answers.long_answers[qId]) {
          level2Answers.long_answers[qId] = window.level2Answers.long_answers[qId];
        }
      });
    }

    // Always include level2Answers in responses (even if all fields are null)
    responses.level2Answers = level2Answers;

    return responses;
  }

  // Level 3 specific response collection
  if (currentLevel === 3) {
    // Initialize level3Answers object - always collect from DOM as source of truth
    // Note: Q1 (identify_emotion MCQ) has been removed
    const collectedLevel3Answers = {
      next_action: null,
      fill_missing_phrase: null,
      long_answers: {}
    };

    // Question 2: Short Answer (next_action) - collect from DOM first, then fallback to object
    const level3Q1 = document.querySelector('.level3-question[data-question-id="1"]');
    if (level3Q1) {
      const textarea = level3Q1.querySelector('.level3-short-answer-textarea');
      if (textarea && textarea.value.trim()) {
        collectedLevel3Answers.next_action = textarea.value.trim();
      }
    }
    // Fallback to object if DOM doesn't have value
    if (!collectedLevel3Answers.next_action && level3Answers.next_action) {
      collectedLevel3Answers.next_action = level3Answers.next_action;
    }

    // Question 3: Fill Missing Phrase (fill_missing_phrase) - collect from DOM first, then fallback to object
    const level3Q2 = document.querySelector('.level3-question[data-question-id="2"]');
    if (level3Q2) {
      const input = level3Q2.querySelector('input');
      if (input && input.value.trim()) {
        collectedLevel3Answers.fill_missing_phrase = input.value.trim();
      }
    }
    // Fallback to object if DOM doesn't have value
    if (!collectedLevel3Answers.fill_missing_phrase && level3Answers.fill_missing_phrase) {
      collectedLevel3Answers.fill_missing_phrase = level3Answers.fill_missing_phrase;
    }

    // Long Answer: Collect from all questions with type "long_answer"
    const longAnswerQuestions = document.querySelectorAll('.level3-question[data-question-type="long_answer"]');
    longAnswerQuestions.forEach(longAnswerQuestion => {
      const questionId = longAnswerQuestion.dataset.questionId;
      const textarea = longAnswerQuestion.querySelector('.level3-long-answer-textarea');
      if (textarea && textarea.value.trim()) {
        collectedLevel3Answers.long_answers[questionId] = textarea.value.trim();
      }
    });
    // Fallback to object if DOM doesn't have values
    if (level3Answers.long_answers && Object.keys(level3Answers.long_answers).length > 0) {
      Object.keys(level3Answers.long_answers).forEach(qId => {
        if (!collectedLevel3Answers.long_answers[qId] && level3Answers.long_answers[qId]) {
          collectedLevel3Answers.long_answers[qId] = level3Answers.long_answers[qId];
        }
      });
    }

    // Defensive check: Remove identify_emotion (Q1) if it somehow exists
    // Q1 has been removed and should never be present, but we ignore it safely if it appears
    if (collectedLevel3Answers.hasOwnProperty('identify_emotion')) {
      console.warn("⚠️ [Defensive] identify_emotion (Q1) found in collected answers - safely ignoring");
      delete collectedLevel3Answers.identify_emotion;
    }

    // Always include level3Answers in responses (even if all fields are null)
    responses.level3Answers = collectedLevel3Answers;

    console.log("📤 Level 3 answers collected from DOM:", collectedLevel3Answers);
    console.log("📤 Global level3Answers object:", level3Answers);

    return responses;
  }

  // Level 1 response collection (existing logic)
  document.querySelectorAll(".question").forEach((q) => {
    const id = q.dataset.questionId;
    // For MCQ, capture the selected radio button
    const radios = q.querySelectorAll('input[type="radio"]');
    if (radios.length > 0) {
      const checked = q.querySelector('input[type="radio"]:checked');
      responses[id] = (checked?.value || "").trim();
    } else {
      // Check if it's an ordering question
      const orderingContainer = q.querySelector(".ordering-container");
      if (orderingContainer) {
        const items = orderingContainer.querySelectorAll(".ordering-item");
        const order = Array.from(items).map(item => item.dataset.value);
        responses[id] = order.join(", ");
      } else {
        // Regular text input
        const input = q.querySelector("input, textarea");
        responses[id] = (input?.value || "").trim();
      }
    }
  });
  return responses;
}

/** 30% threshold - same as backend. */
const LISTENING_PASS_THRESHOLD = 30;

/** True if result indicates user passed listening (can proceed to Speaking). */
function passedListening(result) {
  if (!result) return false;
  if (result.pass === true) return true;
  const score = result.overall_score ?? result.final_listening_score ?? result.accuracy;
  if (score == null) return false;
  const pct = typeof score === 'number' ? (score <= 1 ? score * 100 : score) : 0;
  return pct >= LISTENING_PASS_THRESHOLD;
}

/** Append "Continue with Speaking" at bottom. No pass gate. Pass assessment level so speaking can show Reading only for intermediate. */
function appendContinueToNextTestButton() {
  if (!el.resultDetails) return;
  if (document.getElementById('continue-to-next-test-btn')) return;
  var level = localStorage.getItem('assessmentLevel') || 'basic';
  var rulesUrl = 'speaking-rules.html?level=' + encodeURIComponent(level);
  const continueBtn = document.createElement('a');
  continueBtn.id = 'continue-to-next-test-btn';
  continueBtn.href = rulesUrl;
  continueBtn.textContent = 'Continue with Speaking';
  continueBtn.className = 'btn-primary';
  continueBtn.style.cssText = 'display: inline-block; margin-top: 24px; padding: 14px 28px; text-decoration: none; color: #fff; background: #0a0a0a; border-radius: 8px; font-weight: 600;';
  continueBtn.addEventListener('click', function (e) {
    e.preventDefault();
    sessionStorage.setItem('listeningCompleted', 'true');
    try {
      var r = localStorage.getItem('listeningResults');
      if (r) sessionStorage.setItem('listeningResults', r);
    } catch (err) { }
    window.location.href = rulesUrl;
  });
  el.resultDetails.appendChild(continueBtn);

  // Fallback TeacherAgent Class (if external script fails)
  if (typeof TeacherAgent === 'undefined') {
    window.TeacherAgent = class {
      constructor() {
        this.apiEndpoint = 'http://localhost:5003/api/generate-report';
        this.results = { listening: null, speaking: null, reading: null, writing: null };
      }
      collectResults() {
        const keys = { listening: 'listeningResults', speaking: 'speakingResults', reading: 'readingResults', writing: 'writingResults' };
        for (const [module, key] of Object.entries(keys)) {
          const data = localStorage.getItem(key);
          if (data) { try { this.results[module] = JSON.parse(data); } catch (e) { } }
        }
        return this.results;
      }
      async generateReport() {
        this.collectResults();
        const response = await fetch(this.apiEndpoint, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.results)
        });
        if (!response.ok) throw new Error(`API Error: ${response.status}`);
        const data = await response.json();
        if (data.success && data.report) return data.report;
        throw new Error(data.error || 'Failed to generate report.');
      }
      async downloadPDF(markdown) {
        if (!window.jspdf || !window.marked) {
          alert('PDF libraries not loaded. Please wait and try again.');
          return;
        }
        const { jsPDF } = window.jspdf;
        const doc = new jsPDF();
        const htmlContent = marked.parse(markdown);
        const tempDiv = document.createElement('div');
        tempDiv.style.width = '180mm'; tempDiv.style.padding = '10mm'; tempDiv.style.fontFamily = 'Arial, sans-serif';
        tempDiv.innerHTML = `<div style="color: #0d6efd; border-bottom: 2px solid #0d6efd; padding-bottom: 10px; margin-bottom: 20px;"><h1 style="margin: 0;">Personalized Tamil Assessment Report</h1><p style="margin: 5px 0 0 0;">Generated by AI Teacher Agent</p></div>${htmlContent}`;
        document.body.appendChild(tempDiv);
        try {
          await doc.html(tempDiv, { callback: function (doc) { doc.save('Tamil_Assessment_Report.pdf'); document.body.removeChild(tempDiv); }, x: 10, y: 10, width: 190, windowWidth: 800 });
        } catch (error) {
          const doc2 = new jsPDF();
          doc2.text(doc2.splitTextToSize(markdown.replace(/[#*]/g, ''), 180), 10, 10);
          doc2.save('Tamil_Assessment_Report_Simple.pdf');
          if (tempDiv.parentNode) document.body.removeChild(tempDiv);
        }
      }
    };
  }

  // Add automatic "Teacher FeedBack" section
  if (!document.getElementById('ai-report-summary-section')) {
    const reportSection = document.createElement('div');
    reportSection.id = 'ai-report-summary-section';
    reportSection.style.cssText = 'margin-top: 30px; border-top: 2px dashed #0d6efd; padding-top: 25px; text-align: left;';
    reportSection.innerHTML = `
      <div style="font-size: 1.4rem; font-weight: bold; margin-bottom: 15px; display: flex; align-items: center; gap: 10px;">
          <span>👨‍🏫 AI Teacher's Detailed Feedback</span>
      </div>
      <div id="ai-report-content-box" style="background: #f8f9fa; padding: 20px; border-radius: 8px; border-left: 5px solid #0d6efd;">
          <div id="ai-loading-status" style="display: flex; align-items: center; gap: 10px;">
              <div style="width: 20px; height: 20px; border: 3px solid #f3f3f3; border-top: 3px solid #0d6efd; border-radius: 50%; animation: spin 1s linear infinite;"></div>
              <span>Teacher is reviewing your answers...</span>
          </div>
      </div>
      <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
    `;
    el.resultDetails.appendChild(reportSection);

    // Trigger analysis
    (async () => {
      // Fallback: If for some reason the script didn't initialize the global, try to find it
      if (!window.teacherAgent && typeof TeacherAgent !== 'undefined') {
        window.teacherAgent = new TeacherAgent();
      }

      if (window.teacherAgent) {
        window.teacherAgent.apiEndpoint = 'http://127.0.0.1:5003/api/generate-report';
        try {
          const reportMarkdown = await window.teacherAgent.generateReport();
          const renderedHTML = (typeof marked !== 'undefined') ? marked.parse(reportMarkdown) : reportMarkdown.replace(/\n/g, '<br>');
          document.getElementById('ai-report-content-box').innerHTML = renderedHTML;
        } catch (error) {
          document.getElementById('ai-report-content-box').innerHTML = `<p style="color: #dc3545;">Teacher service unavailable: ${error.message}</p>`;
        }
      }
    })();
  }
}

/** Show "did not pass" message when user failed (no continue button). Dashboard is only on speaking result page. */
function appendDidNotPassMessage() {
  if (!el.resultDetails) return;
  if (document.getElementById('did-not-pass-msg')) return;
  const msg = document.createElement('div');
  msg.id = 'did-not-pass-msg';
  msg.style.cssText = 'margin-top: 24px; padding: 16px 20px; background: #fff3cd; border: 1px solid #ffc107; border-radius: 8px; color: #856404; font-weight: 500;';
  msg.textContent = 'You did not pass the listening test (minimum 30% required). Please try again to proceed to Speaking.';
  el.resultDetails.appendChild(msg);
}

function showResult(result) {
  console.log("📊 Showing result for Level", result.level);
  console.log("📊 Result data:", result);
  console.log("📊 Result details:", result.details);

  // Ensure result has required fields
  if (!result) {
    console.error("❌ showResult called with null/undefined result!");
    return;
  }

  if (result.level === undefined) {
    result.level = 3; // Default to level 3
  }

  // Mark level as completed when result is shown
  localStorage.setItem(`level_${result.level}_completed`, 'true');

  // Re-initialize elements if needed
  if (!el.resultCard || !el.resultSummary || !el.resultDetails) {
    console.log("⚠️ Elements not found, re-initializing...");
    initializeElements();
  }

  // Ensure result card element exists
  if (!el.resultCard) {
    console.error("❌ resultCard element not found after re-initialization!");
    console.error("Available elements:", {
      resultCard: !!document.getElementById("result-card"),
      resultSummary: !!document.getElementById("result-summary"),
      resultDetails: !!document.getElementById("result-details")
    });
    alert("Error: Result card element not found. Please refresh the page.");
    return;
  }

  if (!el.resultSummary) {
    console.error("❌ resultSummary element not found!");
    el.resultSummary = document.getElementById("result-summary");
    if (!el.resultSummary) {
      console.error("❌ resultSummary still not found!");
      return;
    }
  }

  if (!el.resultDetails) {
    console.error("❌ resultDetails element not found!");
    el.resultDetails = document.getElementById("result-details");
    if (!el.resultDetails) {
      console.error("❌ resultDetails still not found!");
      return;
    }
  }

  // Show the result card
  try {
    el.resultCard.style.display = "block";
    el.resultCard.style.visibility = "visible";
    el.resultCard.style.opacity = "1";
    el.resultCard.style.position = "relative"; // Ensure it's in document flow
    console.log("✅ Result card made visible");
  } catch (err) {
    console.error("❌ Error showing result card:", err);
  }

  // Calculate total marks and percentage
  // If level_results is available, show per-level scores and total
  let totalMarks = 0;
  let totalEarnedMarks = 0;
  let levelScores = [];

  if (result.level_results && Array.isArray(result.level_results)) {
    // Calculate per-level scores from level_results
    result.level_results.forEach(levelResult => {
      const level = levelResult.level;
      const questions = levelResult.questions || [];
      let levelEarned = 0;
      let levelTotal = 0;

      // Calculate marks for this level
      questions.forEach(q => {
        const isCorrect = q.status === 'correct';
        let questionMarks = 0;

        if (level === 1) {
          questionMarks = 1; // All Level 1 questions are 1 mark
          levelTotal += 1;
          if (isCorrect) levelEarned += 1;
        } else if (level === 2) {
          // Level 2: Q1=1, Q2=1, Q3=2, Q4=3
          const qNum = parseInt(q.question_id) || 1;
          const marksMap = { 1: 1, 2: 1, 3: 2, 4: 3 };
          questionMarks = marksMap[qNum] || 1;
          levelTotal += questionMarks;
          if (isCorrect) levelEarned += questionMarks;
        } else if (level === 3) {
          // Level 3: Q1=2, Q2=2, Q3=2, Q4=3
          const qNum = parseInt(q.question_id) || 1;
          const marksMap = { 1: 2, 2: 2, 3: 2, 4: 3 };
          questionMarks = marksMap[qNum] || 2;
          levelTotal += questionMarks;
          if (isCorrect) levelEarned += questionMarks;
        }
      });

      levelScores.push({ level, earned: levelEarned, total: levelTotal });
      totalEarnedMarks += levelEarned;
      totalMarks += levelTotal;
    });
  } else {
    // Fallback: calculate from single level result
    if (result.level === 1) {
      totalMarks = 4;
      totalEarnedMarks = result.score || 0;
      levelScores.push({ level: 1, earned: totalEarnedMarks, total: 4 });
    } else if (result.level === 2) {
      totalMarks = 7; // 1+1+2+3
      if (result.details) {
        Object.keys(result.details).forEach(key => {
          const d = result.details[key];
          if (d.correct) {
            const marksMap = { "1": 1, "2": 1, "3": 2, "4": 3 };
            const qNum = key === "identify_speaker" ? "1" :
              key === "dialogue_ordering" ? "2" :
                key === "main_problem_discussed" ? "3" :
                  key === "match_speaker_role" ? "4" : key;
            totalEarnedMarks += marksMap[qNum] || 1;
          }
        });
      } else {
        totalEarnedMarks = result.score || 0;
      }
      levelScores.push({ level: 2, earned: totalEarnedMarks, total: 7 });
    } else if (result.level === 3) {
      totalMarks = 9; // 2+2+2+3
      if (result.details) {
        Object.keys(result.details).forEach(key => {
          const d = result.details[key];
          if (d.correct) {
            const marksMap = { "1": 2, "2": 2, "3": 2, "4": 3 };
            totalEarnedMarks += marksMap[key] || 2;
          }
        });
      } else {
        totalEarnedMarks = result.score || 0;
      }
      levelScores.push({ level: 3, earned: totalEarnedMarks, total: 9 });
    }
  }

  const percentage = totalMarks > 0 ? ((totalEarnedMarks / totalMarks) * 100).toFixed(1) : 0;
  const isPassed = percentage >= 30; // 30% pass threshold

  // Build summary HTML with per-level scores
  let summaryHTML = `
    <div style="font-size: 1.5em; font-weight: bold; margin-bottom: 16px; color: ${isPassed ? '#198754' : '#c0392b'};">
      Total Marks: ${totalEarnedMarks}/${totalMarks} (${percentage}%)
    </div>
  `;

  if (levelScores.length > 0) {
    summaryHTML += `<div style="margin-bottom: 12px; padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    summaryHTML += `<div style="font-weight: bold; margin-bottom: 8px;">Per-Level Scores:</div>`;
    levelScores.forEach(ls => {
      const levelPercentage = ls.total > 0 ? ((ls.earned / ls.total) * 100).toFixed(1) : 0;
      summaryHTML += `
        <div style="margin: 4px 0; font-size: 0.95em;">
          Level ${ls.level}: ${ls.earned}/${ls.total} (${levelPercentage}%)
        </div>
      `;
    });
    summaryHTML += `</div>`;
  }

  summaryHTML += `
    <div style="font-size: 1em; padding: 8px 16px; border-radius: 6px; display: inline-block; background: ${isPassed ? '#d1e7dd' : '#f8d7da'}; color: ${isPassed ? '#0f5132' : '#842029'}; margin-top: 8px;">
      ${isPassed ? '✓ Passed' : '✗ Failed'}
    </div>
  `;

  el.resultSummary.innerHTML = summaryHTML;
  el.resultSummary.style.color = isPassed ? "#198754" : "#c0392b";

  // Clear previous details - don't show individual question details
  el.resultDetails.innerHTML = "";

  console.log("✅ Result summary displayed");

  // Scroll to result card to ensure it's visible
  setTimeout(() => {
    if (el.resultCard) {
      el.resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
      console.log("✅ Scrolled to result card");
    }
  }, 200);

  // Skip all detailed question results and evaluation metrics
  // Only show summary (total marks, per-level scores, pass/fail)
  /*
  if (result.details && typeof result.details === 'object' && Object.keys(result.details).length > 0) {
    console.log("📊 Processing result details:", Object.keys(result.details));
    // Map detail keys to question numbers for Level 2 and Level 3
    const questionKeyMap = {
      // Level 2 mappings
      "identify_speaker": "1",
      "dialogue_ordering": "2",
      "main_problem_discussed": "3",
      "match_speaker_role": "4",
      // Level 3 mappings (IDs 1-4 map directly to Q1-Q4)
      "1": "1",
      "2": "2",
      "3": "3",
      "4": "4",
      // Legacy mappings (for backward compatibility)
      "next_action": "1",
      "fill_missing_phrase": "2"
    };
    
    // Keys to skip for Level 3 (old questions that should not be displayed)
    const skipKeysForLevel3 = ["main_problem_discussed", "main_topic", "Qmain_topic", "identify_emotion"];
    
    Object.keys(result.details).forEach((key) => {
      // Skip long_answers - it will be handled separately (but not for Level 3)
      if (key === "long_answers") {
        return;
      }
    
      // Skip old main_topic questions for Level 3
      if (result.level === 3 && skipKeysForLevel3.includes(key)) {
        return;
      }
      
      // For Level 3, only show questions with IDs 1-4 (skip any other keys)
      if (result.level === 3) {
        const validLevel3Ids = ["1", "2", "3", "4"];
        if (!validLevel3Ids.includes(key) && !questionKeyMap[key]) {
          return; // Skip invalid keys for Level 3
        }
      }

      const d = result.details[key];
      // Use mapped question number if available, otherwise use the key itself (for Level 1)
      const questionNum = questionKeyMap[key] || key;
      
      // Format user_answer for display
      let userAnswerDisplay = "-";
      if (d.user_answer !== null && d.user_answer !== undefined) {
        if (Array.isArray(d.user_answer)) {
          userAnswerDisplay = d.user_answer.join(", ");
        } else if (typeof d.user_answer === 'object') {
          // Handle objects (e.g., match_speaker_role mapping)
          // Format as readable key-value pairs
          try {
            const formattedPairs = Object.entries(d.user_answer)
              .map(([speaker, role]) => `${speaker}: ${role}`)
              .join("; ");
            userAnswerDisplay = formattedPairs || JSON.stringify(d.user_answer, null, 2);
          } catch (e) {
            userAnswerDisplay = JSON.stringify(d.user_answer, null, 2);
            }
        } else {
          userAnswerDisplay = String(d.user_answer);
        }
      }
      
      // Format correct_answer for display
      let correctAnswerDisplay = "-";
      if (d.correct_answer !== null && d.correct_answer !== undefined) {
        if (Array.isArray(d.correct_answer)) {
          correctAnswerDisplay = d.correct_answer.join(", ");
        } else if (typeof d.correct_answer === 'object') {
          // Handle objects (e.g., match_speaker_role mapping)
          // Format as readable key-value pairs
          try {
            const formattedPairs = Object.entries(d.correct_answer)
              .map(([speaker, role]) => `${speaker}: ${role}`)
              .join("; ");
            correctAnswerDisplay = formattedPairs || JSON.stringify(d.correct_answer, null, 2);
          } catch (e) {
            correctAnswerDisplay = JSON.stringify(d.correct_answer, null, 2);
          }
            } else {
          correctAnswerDisplay = String(d.correct_answer);
        }
      }
      
      // Special handling for match_speaker_role to show detailed feedback
      let additionalInfo = "";
      if (key === "match_speaker_role" && !d.correct) {
        const issues = [];
        if (d.incorrect_mappings && d.incorrect_mappings.length > 0) {
          d.incorrect_mappings.forEach(mapping => {
            issues.push(`${mapping.speaker}: got "${mapping.user_role}" but expected "${mapping.correct_role}"`);
          });
        }
        if (d.missing_speakers && d.missing_speakers.length > 0) {
          issues.push(`Missing speakers: ${d.missing_speakers.join(", ")}`);
        }
        if (d.extra_speakers && d.extra_speakers.length > 0) {
          issues.push(`Extra speakers: ${d.extra_speakers.join(", ")}`);
        }
        if (issues.length > 0) {
          additionalInfo = `<div style="margin-top: 8px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; font-size: 0.9em;">
            <strong>Issues:</strong><br>${issues.join("<br>")}
          </div>`;
        }
      }
      
      // Extract evaluation_metrics and show only applicable metrics
      const evalMetrics = d.evaluation_metrics || {};
      const metricsHTML = [];
      
      // Show Accuracy only if it's not null
      if (evalMetrics.accuracy !== null && evalMetrics.accuracy !== undefined) {
        metricsHTML.push(`<div style="margin-top: 8px; padding: 8px; background: #e7f1ff; border-left: 3px solid #0d6efd; font-size: 0.9em;">
          <strong>Accuracy:</strong> ${evalMetrics.accuracy ? "✓ Correct" : "✗ Incorrect"}
        </div>`);
      }
      
      // Show Precision only if it's not null (for MCQs, ordering, matching)
      if (evalMetrics.precision !== null && evalMetrics.precision !== undefined) {
        metricsHTML.push(`<div style="margin-top: 8px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; font-size: 0.9em;">
          <strong>Precision:</strong> ${evalMetrics.precision ? "✓ Exact Match" : "✗ Not Exact"}
        </div>`);
      }
      
      // Show Answer Relevance only if it's not null (for short answers)
      if (evalMetrics.answer_relevance !== null && evalMetrics.answer_relevance !== undefined) {
        metricsHTML.push(`<div style="margin-top: 8px; padding: 8px; background: #d1e7dd; border-left: 3px solid #198754; font-size: 0.9em;">
          <strong>Answer Relevance:</strong> ${evalMetrics.answer_relevance.toFixed(1)}%
        </div>`);
      }
      
      // Get marks for this question
      let questionMarks = 0;
      let questionTotalMarks = 0;
      if (result.level === 1) {
        questionMarks = d.correct ? 1 : 0;
        questionTotalMarks = 1;
      } else if (result.level === 2) {
        const marksMap = { "1": 1, "2": 1, "3": 2, "4": 3 };
        questionTotalMarks = marksMap[questionNum] || 1;
        if (d.marks_earned !== undefined) {
          questionMarks = d.marks_earned;
        } else {
          questionMarks = d.correct ? questionTotalMarks : 0;
        }
      } else if (result.level === 3) {
        const marksMap = { "1": 2, "2": 2, "3": 2, "4": 3 };
        questionTotalMarks = marksMap[questionNum] || 2;
        if (d.marks_earned !== undefined) {
          questionMarks = d.marks_earned;
        } else {
          questionMarks = d.correct ? questionTotalMarks : 0;
        }
      }
      
      const div = document.createElement("div");
      div.className = "detail";
      div.innerHTML = `<div><strong>Q${questionNum}</strong> <span style="color: #666; font-size: 0.9em;">[${questionMarks}/${questionTotalMarks} marks]</span></div>
        <div class="${d.correct ? "correct" : "wrong"}">
          ${d.correct ? "✓ Correct" : "✗ Wrong"} ${questionMarks < questionTotalMarks && questionTotalMarks > 1 ? `(${questionMarks}/${questionTotalMarks} marks)` : ''}
        </div>
        <div>Your answer: ${userAnswerDisplay}</div>
        <div>Expected: ${correctAnswerDisplay}</div>
        ${additionalInfo}
        ${metricsHTML.join("")}`;
      el.resultDetails.appendChild(div);
    });
    
    // Handle long_answer questions separately for Level 2 and Level 3
    // Level 2: Question 5 (L2_Q5) - REMOVED (Level 2 now only has Q1-Q4)
    /*
    if (result.level === 2) {
      const longAnswers = result.details.long_answers || {};
      console.log("🔍 Level 2 Long answers data from backend:", longAnswers);
      console.log("🔍 Available keys:", Object.keys(longAnswers));
      
      // Process L2_Q5 - display it as a separate section below scoring questions
      const targetQuestionId = "L2_Q5";
      const longAnswerKey = `long_answer_${targetQuestionId}`;
      const d = longAnswers[longAnswerKey] || longAnswers["long_answer_5"]; // Try both keys
      console.log(`🔍 Level 2 Q5 (L2_Q5) data (key: ${longAnswerKey}):`, d);
      
      // Get question text from currentQuestions if available
      let questionText = "Question 5 (Long Answer)";
      if (currentQuestions && Array.isArray(currentQuestions)) {
        const q5Data = currentQuestions.find(q => (q.id === targetQuestionId || q.id === "5" || q.question_number === 5) && q.type === "long_answer");
        if (q5Data) {
          questionText = q5Data.question_text_tamil || q5Data.question_text_english || q5Data.question_text || questionText;
        }
      }
      
      // Format user_answer for display - preserve Tamil text exactly as received
      let userAnswerDisplay = "-";
      if (d && d.user_answer !== null && d.user_answer !== undefined && d.user_answer !== "") {
        // Use the exact text as received (no stripping or encoding loss)
        userAnswerDisplay = String(d.user_answer);
        // Truncate if too long for display (only for preview, not for actual text)
        if (userAnswerDisplay.length > 300) {
          userAnswerDisplay = userAnswerDisplay.substring(0, 300) + "...";
        }
      }
      
      // Determine correctness and evaluation status
      const isCorrect = d && d.correct !== null && d.correct !== undefined ? d.correct : false;
      const isEvaluated = d && d.evaluated === true;
      
      // Get answer relevance and key ideas coverage
      // Show percentage if answer_relevance > 0 and evaluation succeeded
      // Only show 0% if evaluation actually failed (evaluated is true and relevance is 0)
      // Otherwise show "N/A" if not evaluated or relevance is null/undefined
      let relevance = "N/A";
      if (isEvaluated && d && d.answer_relevance !== null && d.answer_relevance !== undefined) {
        // If evaluated, show the percentage (including 0% if evaluation failed)
        relevance = `${d.answer_relevance.toFixed(1)}%`;
      }
      
      const coveredCount = d && d.covered_count !== null && d.covered_count !== undefined ? d.covered_count : 0;
      const totalKeyIdeas = d && d.total_key_ideas !== null && d.total_key_ideas !== undefined ? d.total_key_ideas : 0;
      
      // Add separator before long answer section
      const separator = document.createElement("div");
      separator.style.cssText = "margin: 24px 0 16px 0; padding: 12px 0; border-top: 2px solid #dee2e6;";
      el.resultDetails.appendChild(separator);
      
      // Create section header
      const sectionHeader = document.createElement("div");
      sectionHeader.style.cssText = "margin-bottom: 16px; padding: 12px; background: #f8f9fa; border-left: 4px solid #6c757d; border-radius: 4px;";
      sectionHeader.innerHTML = `<h3 style="margin: 0; font-size: 1.1em; color: #495057; font-weight: 600;">Level 2 – Long Answer</h3>`;
      el.resultDetails.appendChild(sectionHeader);
      
      // Create long answer display
      const div = document.createElement("div");
      div.className = "detail";
      div.style.cssText = "margin-top: 12px; padding: 16px; background: #ffffff; border: 2px solid #dee2e6; border-radius: 8px;";
      
      // Create question section - use textContent to preserve Tamil text exactly
      const questionContainer = document.createElement("div");
      questionContainer.style.cssText = "margin-bottom: 12px;";
      const questionLabel = document.createElement("strong");
      questionLabel.style.cssText = "font-size: 1.05em; color: #212529;";
      questionLabel.textContent = "Question:";
      questionContainer.appendChild(questionLabel);
      const questionTextDiv = document.createElement("div");
      questionTextDiv.style.cssText = "margin-top: 6px; padding: 10px; background: #f8f9fa; border-radius: 4px; color: #495057; line-height: 1.6;";
      questionTextDiv.textContent = questionText; // Use textContent to preserve Tamil exactly
      questionContainer.appendChild(questionTextDiv);
      div.appendChild(questionContainer);
      
      // Create user answer section - use textContent to preserve Tamil text exactly
      const answerContainer = document.createElement("div");
      answerContainer.style.cssText = "margin-bottom: 12px;";
      const answerLabel = document.createElement("strong");
      answerLabel.style.cssText = "color: #212529;";
      answerLabel.textContent = "Your answer:";
      answerContainer.appendChild(answerLabel);
      const userAnswerDiv = document.createElement("div");
      userAnswerDiv.style.cssText = "margin-top: 6px; padding: 10px; background: #ffffff; border: 1px solid #ced4da; border-radius: 4px; color: #212529; line-height: 1.6; white-space: pre-wrap; word-wrap: break-word;";
      userAnswerDiv.textContent = userAnswerDisplay; // Use textContent to preserve Tamil exactly
      answerContainer.appendChild(userAnswerDiv);
      div.appendChild(answerContainer);
      
      // Create status section
      const statusContainer = document.createElement("div");
      statusContainer.style.cssText = "margin-bottom: 12px;";
      statusContainer.innerHTML = `
        <strong style="color: #212529;">Status:</strong>
        <div style="margin-top: 6px;">
          <span class="${isCorrect ? "correct" : "wrong"}" style="display: inline-block; padding: 6px 12px; border-radius: 4px; font-weight: 600;">
            ${isEvaluated ? (isCorrect ? "Correct" : "Wrong") : "Not Evaluated"}
          </span>
        </div>
      `;
      div.appendChild(statusContainer);
      
      // Create relevance section - only show if evaluated and relevance is available
      if (isEvaluated && d && d.answer_relevance !== null && d.answer_relevance !== undefined) {
        const relevanceContainer = document.createElement("div");
        relevanceContainer.style.cssText = "margin-bottom: 12px;";
        relevanceContainer.innerHTML = `
          <strong style="color: #212529;">Answer Relevance:</strong>
          <div style="margin-top: 6px; padding: 10px; background: ${isCorrect ? '#d1e7dd' : '#f8d7da'}; border-left: 4px solid ${isCorrect ? '#198754' : '#dc3545'}; border-radius: 4px;">
            <span style="font-size: 1.1em; font-weight: 600; color: ${isCorrect ? '#0f5132' : '#842029'};">
              ${relevance}
            </span>
          </div>
        `;
        div.appendChild(relevanceContainer);
      }
      
      // Create key ideas covered section - only show if evaluated
      if (isEvaluated && totalKeyIdeas > 0) {
        const keyIdeasContainer = document.createElement("div");
        keyIdeasContainer.style.cssText = "margin-bottom: 12px;";
        keyIdeasContainer.innerHTML = `
          <strong style="color: #212529;">Key Ideas Covered:</strong>
          <div style="margin-top: 6px; padding: 10px; background: #e7f1ff; border-left: 4px solid #0d6efd; border-radius: 4px;">
            <span style="font-size: 1.1em; font-weight: 600; color: #084298;">
              ${coveredCount} / ${totalKeyIdeas}
            </span>
          </div>
        `;
        div.appendChild(keyIdeasContainer);
      }
      
      // Create evaluation note for long answers
      const noteContainer = document.createElement("div");
      noteContainer.style.cssText = "margin-top: 12px; padding: 8px; background: #d1e7dd; border-left: 3px solid #198754; border-radius: 4px;";
      noteContainer.innerHTML = '<em style="color: #0f5132; font-size: 0.9em; font-weight: 500;">Evaluated on semantic relevance only</em>';
      div.appendChild(noteContainer);
      
      el.resultDetails.appendChild(div);
    }
    */

  // Level 3: Only Q3 and Q4 are long answers (IDs 3 and 4)
  // Skip long_answers processing for Level 3 since Q3 and Q4 are already in main details
  // Level 3 now has only 4 questions (IDs 1-4), all handled in main details loop above
  if (result.level === 3) {
    // Level 3 questions are already displayed in the main details loop above
    // No need to process long_answers separately since all questions use the same details structure
    console.log("✅ Level 3 questions already displayed in main details loop");
  }

  // Legacy code for old Level 3 structure (commented out - Level 3 now uses IDs 1-4 directly)
  /*
  if (result.level === 3) {
    const longAnswers = result.details.long_answers || {};
    console.log("🔍 Long answers data from backend:", longAnswers);
    console.log("🔍 Available keys:", Object.keys(longAnswers));
    
    // Process only Q3 and Q4 (IDs 3 and 4) - Q5 no longer exists
    ["3", "4"].forEach((qId) => {
      const longAnswerKey = `long_answer_${qId}`;
      const d = longAnswers[longAnswerKey];
      console.log(`🔍 Q${qId} data (key: ${longAnswerKey}):`, d);
      
      // Always display Q4 and Q5 (even if evaluation data is missing)
      
      // Format user_answer for display - preserve Tamil text exactly as received
      let userAnswerDisplay = "-";
      if (d && d.user_answer !== null && d.user_answer !== undefined && d.user_answer !== "") {
        // Use the exact text as received (no stripping or encoding loss)
        userAnswerDisplay = String(d.user_answer);
        // Truncate if too long for display (only for preview, not for actual text)
        if (userAnswerDisplay.length > 200) {
          userAnswerDisplay = userAnswerDisplay.substring(0, 200) + "...";
        }
      }
      
      // Format expected answer - show key ideas summary for long answers (preserve Tamil)
      let expectedDisplay = "Long answer evaluation";
      if (d && d.key_ideas && Array.isArray(d.key_ideas) && d.key_ideas.length > 0) {
        // Show first 2-3 key ideas as summary (preserve Tamil text)
        const keyIdeaTexts = d.key_ideas.slice(0, 2).map(idea => {
          if (typeof idea === 'object' && idea.tamil) {
            return idea.tamil; // Preserve Tamil text exactly
          }
          return String(idea);
        });
        expectedDisplay = keyIdeaTexts.join("; ") + (d.key_ideas.length > 2 ? "..." : "");
      }
      
      // Determine correctness and evaluation status
      const isCorrect = d && d.correct !== null && d.correct !== undefined ? d.correct : false;
      const isEvaluated = d && d.evaluated === true;
      
      // Additional info for long answers - show only Answer Relevance, Key Ideas Covered, and note
      let additionalInfo = "";
      if (d && isEvaluated) {
        let relevance = "N/A";
        if (d.answer_relevance !== null && d.answer_relevance !== undefined) {
          // If evaluated, show the percentage (including 0% if evaluation failed)
          relevance = `${d.answer_relevance.toFixed(1)}%`;
        }
        const coveredCount = d.covered_count !== null && d.covered_count !== undefined ? d.covered_count : 0;
        const totalKeyIdeas = d.total_key_ideas !== null && d.total_key_ideas !== undefined ? d.total_key_ideas : 0;
        
        // Build metrics HTML - only show Answer Relevance and Key Ideas Covered
        const metricsParts = [];
        
        // Show Answer Relevance if available
        if (d.answer_relevance !== null && d.answer_relevance !== undefined) {
          metricsParts.push(`<div style="margin-top: 8px; padding: 8px; background: ${isCorrect ? '#d1e7dd' : '#f8d7da'}; border-left: 3px solid ${isCorrect ? '#198754' : '#dc3545'}; font-size: 0.9em;">
            <strong>Answer Relevance:</strong> ${relevance}
          </div>`);
        }
        
        // Show Key Ideas Covered if available
        if (totalKeyIdeas > 0) {
          metricsParts.push(`<div style="margin-top: 8px; padding: 8px; background: #e7f1ff; border-left: 3px solid #0d6efd; font-size: 0.9em;">
            <strong>Key Ideas Covered:</strong> ${coveredCount} / ${totalKeyIdeas}
          </div>`);
        }
        
        // Add evaluation note
        metricsParts.push(`<div style="margin-top: 8px; padding: 8px; background: #d1e7dd; border-left: 3px solid #198754; font-size: 0.9em;">
          <em style="color: #0f5132; font-weight: 500;">Evaluated on semantic relevance only</em>
        </div>`);
        
        additionalInfo = metricsParts.join("");
      } else if (d) {
        // Show placeholder if not yet evaluated
        additionalInfo = `<div style="margin-top: 8px; padding: 8px; background: #fff3cd; border-left: 3px solid #ffc107; font-size: 0.9em;">
          <em style="color: #856404;">Evaluation pending or not available</em>
        </div>`;
      } else {
        // No data available
        additionalInfo = `<div style="margin-top: 8px; padding: 8px; background: #e2e3e5; border-left: 3px solid #6c757d; font-size: 0.9em;">
          <em style="color: #6c757d;">No evaluation data available</em>
        </div>`;
      }
      
      const div = document.createElement("div");
      div.className = "detail";
      div.innerHTML = `<div><strong>Q${qId}</strong> <span style="color: #6c757d; font-size: 0.85em;">(Long Answer - Non-scoring)</span></div>
        <div class="${isCorrect ? "correct" : "wrong"}">
          ${isEvaluated ? (isCorrect ? "Correct" : "Wrong") : "Not Evaluated"}
        </div>
        <div>Your answer: ${userAnswerDisplay}</div>
        <div>Key Ideas (summary): ${expectedDisplay}</div>
          ${additionalInfo}`;
      el.resultDetails.appendChild(div);
    });
  }
  */

  // Update submit button text based on level
  if (el.submitBtn) {
    if (currentLevel < 3) {
      el.submitBtn.textContent = "Next Level →";
    } else {
      el.submitBtn.textContent = "Submit Answers";
    }
  }

  // Hide next level button (we use submit button instead)
  if (el.nextLevelBtn) {
    el.nextLevelBtn.style.display = "none";
  }

  // Skip overall results section - only show summary
  // Removed: "See Overall Results" button and detailed evaluation metrics
}

// Fetch final evaluation with trigger_final_evaluation = true
async function fetchFinalEvaluation() {
  // Collect current responses to resubmit Level 3 with trigger flag
  const responses = collectResponses();

  const payload = {
    audio_id: currentAudioId,
    responses: responses,
    level: 3,
    trigger_final_evaluation: true
  };

  console.log("📤 Fetching final evaluation with trigger_final_evaluation=true:", payload);

  const result = await fetchJson(`${API_BASE_URL}/evaluate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }, 360000);

  console.log("📥 Final evaluation response received:", result);
  return result;
}

// Render overall results with pie charts and learner level
function renderOverallResults(container, result) {
  container.innerHTML = '';

  // Section header
  const header = document.createElement('h3');
  header.style.cssText = 'margin: 0 0 20px 0; font-size: 1.3em; color: #2f2f46; font-weight: 600;';
  header.textContent = 'மொத்த மதிப்பீடு / Overall Evaluation';
  container.appendChild(header);

  // Charts container - grid layout for three pie charts
  const chartsContainer = document.createElement('div');
  chartsContainer.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 24px; margin-bottom: 24px;';

  // Helper function to create pie chart
  function createPieChart(canvasId, title, value, valueLabel, complementLabel, colors) {
    // Handle null/undefined values
    let percentage = 0;
    if (value !== null && value !== undefined) {
      percentage = typeof value === 'number' ? (value <= 1 ? value * 100 : value) : 0;
    }

    const complement = 100 - percentage;

    const chartContainer = document.createElement('div');
    chartContainer.style.cssText = 'background: #ffffff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);';

    // Chart title (Tamil / English)
    const chartTitle = document.createElement('div');
    chartTitle.style.cssText = 'text-align: center; margin-bottom: 16px; font-weight: 600; font-size: 1.1em; color: #2f2f46;';
    chartTitle.textContent = title;
    chartContainer.appendChild(chartTitle);

    // Canvas for chart
    const canvas = document.createElement('canvas');
    canvas.id = canvasId;
    canvas.style.cssText = 'max-height: 250px;';
    chartContainer.appendChild(canvas);

    // Percentage display below chart
    const percentageDisplay = document.createElement('div');
    percentageDisplay.style.cssText = 'text-align: center; margin-top: 12px; font-size: 1.3em; font-weight: 700; color: ' + colors.positive + ';';
    percentageDisplay.textContent = percentage.toFixed(1) + '%';
    chartContainer.appendChild(percentageDisplay);

    chartsContainer.appendChild(chartContainer);

    // Create chart after a short delay (skip if Chart.js blocked by tracking prevention)
    setTimeout(function () {
      try {
        if (typeof Chart !== 'undefined') {
          new Chart(canvas, {
            type: 'pie',
            data: {
              labels: [valueLabel, complementLabel],
              datasets: [{
                data: [percentage, complement],
                backgroundColor: [colors.positive, colors.negative],
                borderColor: '#ffffff',
                borderWidth: 3
              }]
            },
            options: {
              responsive: true,
              maintainAspectRatio: true,
              plugins: {
                legend: { position: 'bottom', labels: { padding: 12, font: { size: 12 } } },
                tooltip: { callbacks: { label: function (c) { return c.label + ': ' + c.parsed.toFixed(1) + '%'; } } }
              }
            }
          });
        }
      } catch (chartErr) {
        console.warn('Chart.js skipped (e.g. tracking prevention):', chartErr.message);
      }
    }, 100);
  }

  // Create Accuracy pie chart (use accuracy from result, not overall_accuracy)
  const accuracy = result.accuracy !== undefined ? result.accuracy : result.overall_accuracy;
  if (accuracy !== undefined) {
    createPieChart(
      'accuracyChart',
      'துல்லியம் / Accuracy',
      accuracy,
      'Correct',
      'Incorrect',
      {
        positive: '#198754', // Green
        negative: '#dc3545'  // Red
      }
    );
  }

  // Create Precision pie chart (use precision from result, not overall_precision)
  const precision = result.precision !== undefined ? result.precision : result.overall_precision;
  if (precision !== undefined) {
    createPieChart(
      'precisionChart',
      'சரியான பொருத்தம் / Precision',
      precision,
      'Precise',
      'Imprecise',
      {
        positive: '#0d6efd', // Blue
        negative: '#6c757d'  // Grey
      }
    );
  }

  // Create Answer Relevance pie chart (use answer_relevance from result, not overall_answer_relevance)
  const answerRelevance = result.answer_relevance !== undefined ? result.answer_relevance : result.overall_answer_relevance;
  if (answerRelevance !== undefined) {
    createPieChart(
      'answerRelevanceChart',
      'பதில் பொருத்தம் / Answer Relevance',
      answerRelevance,
      'Relevant',
      'Irrelevant',
      {
        positive: '#6f42c1', // Purple
        negative: '#adb5bd'  // Light grey
      }
    );
  }

  container.appendChild(chartsContainer);

  // Determine learner level and color based on learner_level from backend
  const learnerLevel = result.learner_level || 'Beginner';
  let levelColor = '#6c757d';
  if (learnerLevel === 'Beginner') {
    levelColor = '#dc3545'; // Red
  } else if (learnerLevel === 'Intermediate') {
    levelColor = '#ffc107'; // Yellow/Orange
  } else if (learnerLevel === 'Pro') {
    levelColor = '#198754'; // Green
  }

  // Learner Level text below charts
  const learnerLevelDiv = document.createElement('div');
  learnerLevelDiv.style.cssText = 'margin-top: 24px; padding: 20px; background: #ffffff; border-radius: 12px; border-left: 4px solid ' + levelColor + '; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;';
  learnerLevelDiv.innerHTML = `
    <div style="font-size: 1.2em; font-weight: 600; color: #495057; line-height: 1.6;">
      This person is a <strong style="color: ${levelColor}; font-size: 1.1em;">${learnerLevel}</strong> in the listening assessment of this language.
        </div>
    `;
  container.appendChild(learnerLevelDiv);
}

/**
 * Render evaluation report at bottom of page (terminal-style data in professional card layout).
 * Shows level-wise scores, Accuracy, Precision, Answer Relevance, Overall Score, Learner Level.
 */
function renderEvaluationReportBottom(container, result) {
  if (!container || !result) return;
  container.id = 'evaluation-report-bottom';
  container.style.cssText = 'margin-top: 32px; padding: 0; width: 100%;';
  container.innerHTML = '';

  const sectionTitle = document.createElement('h3');
  sectionTitle.style.cssText = 'margin: 0 0 20px 0; font-size: 1.35em; color: #1a1a1a; font-weight: 700; padding-bottom: 12px; border-bottom: 2px solid rgba(0,0,0,0.08);';
  sectionTitle.textContent = 'Evaluation Report | மதிப்பீடு அறிக்கை';
  container.appendChild(sectionTitle);

  const cardStyle = 'background: #fff; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 20px 24px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.06);';

  // Level-wise results
  const levelResults = result.level_results || [];
  levelResults.forEach(function (lr) {
    const level = lr.level;
    const questions = lr.questions || [];
    const correct = questions.filter(function (q) { return q.status === 'correct'; }).length;
    const total = questions.length;
    const pct = total > 0 ? ((correct / total) * 100).toFixed(1) : 0;

    const levelCard = document.createElement('div');
    levelCard.style.cssText = cardStyle;
    levelCard.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 12px;">
        <span style="font-size: 1.15em; font-weight: 700; color: #1a1a1a;">Level ${level}</span>
        <span style="font-size: 1.1em; font-weight: 600; color: #0a0a0a;">Score: ${correct}/${total} (${pct}%)</span>
      </div>
      <div style="display: grid; gap: 8px;">
        ${questions.map(function (q, i) {
      const isCorrect = q.status === 'correct';
      const dot = isCorrect ? '●' : '○';
      const color = isCorrect ? '#198754' : '#dc3545';
      const label = isCorrect ? 'Correct' : 'Wrong';
      return `<div style="font-size: 0.95em; color: #444;"><span style="color: ${color}; font-weight: 600;">${dot} Q${i + 1}</span> — ${label}</div>`;
    }).join('')}
      </div>
    `;
    container.appendChild(levelCard);
  });

  // Metrics row: Accuracy, Precision, Answer Relevance
  const acc = result.accuracy != null ? (result.accuracy <= 1 ? result.accuracy * 100 : result.accuracy) : 0;
  const prec = result.precision != null ? (result.precision <= 1 ? result.precision * 100 : result.precision) : 0;
  const rel = result.answer_relevance != null ? (result.answer_relevance <= 1 ? result.answer_relevance * 100 : result.answer_relevance) : 0;
  const overall = result.overall_score != null ? (result.overall_score <= 1 ? result.overall_score * 100 : result.overall_score) : 0;
  const learnerLevel = result.learner_level || 'Beginner';

  const metricsCard = document.createElement('div');
  metricsCard.style.cssText = cardStyle;
  metricsCard.innerHTML = `
    <div style="font-size: 1.1em; font-weight: 700; color: #1a1a1a; margin-bottom: 16px;">Summary</div>
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px;">
      <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 8px;">
        <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">Accuracy</div>
        <div style="font-size: 1.4em; font-weight: 700; color: #198754;">${Number(acc).toFixed(1)}%</div>
      </div>
      <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 8px;">
        <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">Precision</div>
        <div style="font-size: 1.4em; font-weight: 700; color: #0d6efd;">${Number(prec).toFixed(1)}%</div>
      </div>
      <div style="text-align: center; padding: 12px; background: #f8f9fa; border-radius: 8px;">
        <div style="font-size: 0.85em; color: #666; margin-bottom: 4px;">Answer Relevance</div>
        <div style="font-size: 1.4em; font-weight: 700; color: #6f42c1;">${Number(rel).toFixed(1)}%</div>
      </div>
    </div>
    <div style="margin-top: 20px; padding-top: 16px; border-top: 1px solid rgba(0,0,0,0.08); display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">
      <div>
        <span style="font-size: 0.9em; color: #666;">Overall Score</span>
        <span style="font-size: 1.6em; font-weight: 700; color: #0a0a0a; margin-left: 8px;">${Number(overall).toFixed(1)}%</span>
      </div>
      <div style="padding: 8px 16px; background: #0a0a0a; color: #fff; border-radius: 8px; font-weight: 600;">
        Learner Level: ${learnerLevel}
      </div>
    </div>
  `;
  container.appendChild(metricsCard);

  // Auto-generate AI Teacher Report at the end of the evaluation
  if (typeof TeacherAgent !== 'undefined') {
    const aiTeacher = new TeacherAgent();
    // Use setTimeout to allow the UI to render the metrics first
    setTimeout(async () => {
      container.innerHTML += `
        <div id="ai-teacher-loading" class="ai-report-card" style="margin-top: 30px; text-align: center;">
            <div class="loading-ai">
                <div class="spinner-ai"></div>
                <p>Professor is analyzing your performance...</p>
            </div>
        </div>
      `;
      try {
        const markdown = await aiTeacher.generateReport();
        const html = typeof marked !== 'undefined' ? marked.parse(markdown) : `<p>${markdown}</p>`;
        const loadingEl = document.getElementById('ai-teacher-loading');
        if (loadingEl) {
          loadingEl.outerHTML = `
                <div class="ai-teacher-section">
                    <h2 style="font-size: 1.8rem; margin-bottom: 15px; text-align: center; color: #1a1a1a;">👨‍🏫 AI Teacher Report</h2>
                    <div class="ai-report-card">
                        <div class="ai-report-content">
                            ${html}
                            
                            <div style="margin-top: 40px; text-align: center;">
                                <button onclick="new TeacherAgent().downloadPDF(unescape('${escape(markdown).replace(/'/g, "\\'")}'))" class="pdf-btn">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
                                    Download Academic Report (PDF)
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
              `;
        }
      } catch (err) {
        const loadingEl = document.getElementById('ai-teacher-loading');
        if (loadingEl) loadingEl.innerHTML = `<p style="color: red;">Failed to load report: ${err.message}</p>`;
      }
    }, 500);
  } else {
    console.warn("⚠️ TeacherAgent class not found. Ensure teacher-agent.js is loaded.");
  }
}

// Validate Level 2 answers before submission
function validateLevel1Answers() {
  // Safety check: Only validate Level 1 answers when currentLevel === 1
  if (currentLevel !== 1) {
    console.warn("⚠️ validateLevel1Answers called but currentLevel is not 1. Skipping validation.");
    return null;
  }

  // Check Question 1: fill_blank (text input)
  const question1 = document.querySelector('.question[data-question-id="1"]');
  if (question1) {
    // Check for any input element (not just type="text" since type might not be explicitly set)
    const input = question1.querySelector('input:not([type="radio"]):not([type="checkbox"])');
    if (!input || !input.value || !input.value.trim()) {
      console.log("❌ Question 1 validation failed:", { input: input, value: input?.value });
      return 1;
    }
  } else {
    console.log("❌ Question 1 element not found");
    return 1;
  }

  // Check Question 2: MCQ (radio buttons)
  const question2 = document.querySelector('.question[data-question-id="2"]');
  if (question2) {
    const checkedRadio = question2.querySelector('input[type="radio"]:checked');
    if (!checkedRadio) {
      console.log("❌ Question 2 validation failed: No radio button selected");
      return 2;
    }
  } else {
    console.log("❌ Question 2 element not found");
    return 2;
  }

  // Check Question 3: short_answer (text input)
  const question3 = document.querySelector('.question[data-question-id="3"]');
  if (question3) {
    // Check for any input element (not just type="text" since type might not be explicitly set)
    const input = question3.querySelector('input:not([type="radio"]):not([type="checkbox"])');
    if (!input || !input.value || !input.value.trim()) {
      console.log("❌ Question 3 validation failed:", { input: input, value: input?.value });
      return 3;
    }
  } else {
    console.log("❌ Question 3 element not found");
    return 3;
  }

  // Check Question 4: ordering (drag and drop items)
  const question4 = document.querySelector('.question[data-question-id="4"]');
  if (question4) {
    const orderingContainer = question4.querySelector('.ordering-container');
    if (!orderingContainer) {
      console.log("❌ Question 4 validation failed: ordering-container not found");
      return 4;
    } else {
      const items = orderingContainer.querySelectorAll('.ordering-item');
      if (!items || items.length === 0) {
        console.log("❌ Question 4 validation failed: No ordering items found");
        return 4;
      }
    }
  } else {
    console.log("❌ Question 4 element not found");
    return 4;
  }

  // All questions are answered
  console.log("✅ All Level 1 questions validated successfully");
  return null;
}

function validateLevel2Answers() {
  // Safety check: Only validate Level 2 answers when currentLevel === 2
  if (currentLevel !== 2) {
    console.warn("⚠️ validateLevel2Answers called but currentLevel is not 2. Skipping validation.");
    return null;
  }

  // Check Question 1: MCQ (identify_speaker)
  const level2Q1 = document.querySelector('.level2-question[data-question-id="1"]');
  if (level2Q1) {
    const checkedRadio = level2Q1.querySelector('input[type="radio"]:checked');
    if (!checkedRadio) {
      return 1;
    }
  } else {
    return 1;
  }

  // Check Question 2: Dialogue Ordering (dialogue_ordering)
  const level2Q2 = document.querySelector('.level2-question[data-question-id="2"]');
  if (level2Q2) {
    const orderingList = level2Q2.querySelector('.dialogue-ordering-list');
    if (!orderingList) {
      return 2;
    } else {
      const items = orderingList.querySelectorAll('.level2-ordering-item');
      if (!items || items.length === 0) {
        return 2;
      }
    }
  } else {
    return 2;
  }

  // Check Question 3: Short Answer (main_problem_discussed)
  const level2Q3 = document.querySelector('.level2-question[data-question-id="3"]');
  if (level2Q3) {
    const textarea = level2Q3.querySelector('.level2-short-answer-textarea');
    if (!textarea || !textarea.value.trim()) {
      return 3;
    }
  } else {
    return 3;
  }

  // Check Question 4: Match Speaker Role (match_speaker_role)
  const level2Q4 = document.querySelector('.level2-question[data-question-id="4"]');
  if (level2Q4) {
    const matchingContainer = level2Q4.querySelector('.speaker-role-matching-container');
    if (!matchingContainer) {
      return 4;
    } else {
      // Check if using dropdown/select interface (new method)
      const selects = matchingContainer.querySelectorAll('.speaker-role-select');
      if (selects.length > 0) {
        // Using dropdown/select interface
        const speakersWithoutRoles = [];
        selects.forEach(select => {
          const speaker = select.dataset.speaker;
          const selectedRole = select.value;
          if (!selectedRole || selectedRole.trim() === "") {
            speakersWithoutRoles.push(speaker);
            console.log(`❌ Speaker "${speaker}" missing role (dropdown)`);
          }
        });

        if (speakersWithoutRoles.length > 0) {
          return 4;
        }
      } else {
        // Legacy drag-and-drop interface
        const speakerBoxes = matchingContainer.querySelectorAll('.speaker-box');
        const speakersWithoutRoles = [];

        speakerBoxes.forEach(speakerBox => {
          const speaker = speakerBox.dataset.speaker;
          const roleMatchArea = speakerBox.querySelector('.role-match-area');

          // Check if speaker has a role assigned
          const hasRoleText = roleMatchArea &&
            roleMatchArea.dataset.roleText &&
            roleMatchArea.dataset.roleText.trim() !== "";
          const isVisible = roleMatchArea &&
            roleMatchArea.style.display !== "none" &&
            roleMatchArea.offsetParent !== null;
          const hasTextContent = roleMatchArea &&
            roleMatchArea.textContent &&
            roleMatchArea.textContent.trim() !== "" &&
            roleMatchArea.textContent.trim() !== "பாத்திர விளக்கம் இங்கே விடவும் / Drop role here";

          if (!hasRoleText || !isVisible || !hasTextContent) {
            speakersWithoutRoles.push(speaker);
          }
        });

        if (speakersWithoutRoles.length > 0) {
          return 4;
        }
      }
    }
  } else {
    return 4;
  }

  // All questions are answered
  return null;
}

// Function to validate Level 3 answers - checks that all 4 remaining questions (Q2, Q3, Q4, Q5) are answered
function validateLevel3Answers() {
  // Safety check: Only validate Level 3 answers when currentLevel === 3
  if (currentLevel !== 3) {
    console.warn("⚠️ validateLevel3Answers called but currentLevel is not 3. Skipping validation.");
    return null;
  }

  // Check Question 1 (UI) - internal ID "2" (next_action): Short answer textarea
  const level3Q1 = document.querySelector('.level3-question[data-question-id="1"]');
  if (level3Q1) {
    const textarea = level3Q1.querySelector('.level3-short-answer-textarea');
    if (!textarea || !textarea.value.trim()) {
      return 1; // UI question number 1
    }
  } else {
    return 1;
  }

  // Check Question 2 (UI) - internal ID "3" (fill_missing_phrase): Text input
  const level3Q2 = document.querySelector('.level3-question[data-question-id="2"]');
  if (level3Q2) {
    const input = level3Q2.querySelector('input');
    if (!input || !input.value.trim()) {
      return 2; // UI question number 2
    }
  } else {
    return 2;
  }

  // Check Question 3 (UI) - internal ID "4" (long_answer): Textarea
  const level3Q3 = document.querySelector('.level3-question[data-question-id="3"]');
  if (level3Q3) {
    const textarea = level3Q3.querySelector('.level3-long-answer-textarea');
    if (!textarea || !textarea.value.trim()) {
      return 3; // UI question number 3
    }
  } else {
    return 3;
  }

  // Check Question 4 (UI) - internal ID "5" (long_answer): Textarea
  const level3Q4 = document.querySelector('.level3-question[data-question-id="4"]');
  if (level3Q4) {
    const textarea = level3Q4.querySelector('.level3-long-answer-textarea');
    if (!textarea || !textarea.value.trim()) {
      return 4; // UI question number 4
    }
  } else {
    return 4;
  }

  // All questions are answered
  return null;
}

async function submitAnswers() {
  if (!currentAudioId) {
    alert("Audio not loaded. Please choose a level again.");
    return;
  }

  // Capture "Next Level" intent BEFORE changing button text (evaluation only after Level 3 Submit)
  const isNextLevelAction = el.submitBtn && el.submitBtn.textContent.includes("Next Level");

  // Validate current level - check if any question is unanswered
  let missingQuestionNumber = null;
  if (currentLevel === 1) {
    missingQuestionNumber = validateLevel1Answers();
  } else if (currentLevel === 2) {
    missingQuestionNumber = validateLevel2Answers();
  } else if (currentLevel === 3) {
    missingQuestionNumber = validateLevel3Answers();
  }

  if (missingQuestionNumber !== null) {
    alert(`Please answer Question ${missingQuestionNumber} before submitting.`);
    if (el.submitBtn) {
      el.submitBtn.disabled = false;
      el.submitBtn.textContent = currentLevel < 3 ? "Next Level →" : "Submit Answers";
    }
    return;
  }

  // "Next Level" clicked (Level 1 or 2): save answers locally and open next level only; no backend submit
  if (isNextLevelAction && currentLevel < 3) {
    const responses = collectResponses();
    if (currentLevel === 2) {
      if (!responses.level2Answers) responses.level2Answers = {};
      responses.level2Answers = {
        identify_speaker: null,
        dialogue_ordering: null,
        main_problem_discussed: null,
        match_speaker_role: null,
        ...responses.level2Answers
      };
    }
    localStorage.setItem(`level_${currentLevel}_answers`, JSON.stringify(responses));
    const nextLevel = currentLevel + 1;
    console.log(`➡️ Going to Level ${nextLevel} (evaluation only after Level 3 Submit).`);
    window.history.pushState({}, '', `?level=${nextLevel}`);
    currentLevel = nextLevel;
    localStorage.setItem('currentTestLevel', nextLevel.toString());
    if (el.submitBtn) {
      el.submitBtn.disabled = true;
      el.submitBtn.textContent = "Loading...";
    }
    await loadLevel(nextLevel);
    window.scrollTo({ top: 0, behavior: 'smooth' });
    if (el.submitBtn) {
      el.submitBtn.disabled = false;
      el.submitBtn.textContent = nextLevel < 3 ? "Next Level →" : "Submit Answers";
    }
    return;
  }

  // Level 3 "Submit Answers" clicked - submit all 3 levels to backend and run evaluation
  el.submitBtn.disabled = true;
  el.submitBtn.textContent = "Submitting... (this may take up to 2 minutes)";

  const responses = collectResponses();

  if (currentLevel === 2) {
    if (!responses.level2Answers) responses.level2Answers = {};
    responses.level2Answers = {
      identify_speaker: null,
      dialogue_ordering: null,
      main_problem_discussed: null,
      match_speaker_role: null,
      ...responses.level2Answers
    };
    console.log("📤 Level 2 answers to submit:", responses.level2Answers);
  }

  if (currentLevel === 3) {
    if (!responses.level3Answers) responses.level3Answers = {};
    if (responses.level3Answers && responses.level3Answers.hasOwnProperty('identify_emotion')) {
      delete responses.level3Answers.identify_emotion;
    }
    responses.level3Answers = {
      next_action: null,
      fill_missing_phrase: null,
      ...responses.level3Answers
    };
    if (responses.level3Answers && responses.level3Answers.hasOwnProperty('identify_emotion')) {
      delete responses.level3Answers.identify_emotion;
    }
    console.log("📤 Level 3 answers to submit:", responses.level3Answers);
  }

  localStorage.setItem(`level_${currentLevel}_answers`, JSON.stringify(responses));

  // Submit button on Level 3 - submit all levels and show results (no confirmation popup)
  // Collect all answers from all levels
  const allLevelAnswers = {
    level1: JSON.parse(localStorage.getItem('level_1_answers') || '{}'),
    level2: JSON.parse(localStorage.getItem('level_2_answers') || '{}'),
    level3: JSON.parse(localStorage.getItem('level_3_answers') || '{}')
  };

  // Mark all levels as completed
  localStorage.setItem('level_1_completed', 'true');
  localStorage.setItem('level_2_completed', 'true');
  localStorage.setItem('level_3_completed', 'true');

  // Now submit all levels and evaluate
  const triggerFinalEvaluation = true;

  // Do full evaluation (timer continues running)
  // NOTE: Timer continues running during evaluation - DO NOT STOP IT

  // All 3 levels will be submitted - show loading indicator and start evaluation
  el.submitBtn.disabled = true;
  el.submitBtn.textContent = "Processing Evaluation... (Timer continues)";

  // Show loading indicator
  const loadingIndicator = document.createElement('div');
  loadingIndicator.id = 'evaluation-loading';
  loadingIndicator.style.cssText = `
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    padding: 30px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    z-index: 10000;
    text-align: center;
    min-width: 300px;
  `;
  loadingIndicator.innerHTML = `
    <div style="font-size: 28px; margin-bottom: 16px;">⏳</div>
    <div style="font-size: 20px; font-weight: 700; margin-bottom: 12px; color: #1a1a1a;">Evaluation is in progress</div>
    <div style="font-size: 15px; color: #444; margin-bottom: 10px; line-height: 1.5;">The server is evaluating Level 1, then Level 2, then Level 3.</div>
    <div style="font-size: 14px; color: #666; margin-bottom: 16px;">This may take 1–3 minutes. Please do not close this page.</div>
    <div style="font-size: 12px; color: #999;">Timer continues running during evaluation</div>
    <div style="margin-top: 20px;">
      <div style="border: 3px solid #f3f3f3; border-top: 3px solid #0a0a0a; border-radius: 50%; width: 44px; height: 44px; animation: spin 1s linear infinite; margin: 0 auto;"></div>
    </div>
    <style>
      @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
      }
    </style>
  `;
  document.body.appendChild(loadingIndicator);

  // Submit all 3 levels to backend for evaluation (async - timer continues)
  console.log("📤 Submitting all 3 levels for final evaluation...");

  try {
    // Submit Level 1
    const level1Answers = allLevelAnswers.level1;
    if (Object.keys(level1Answers).length > 0) {
      await fetchJson(`${API_BASE_URL}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_id: levelAudioMap[1] || "level1",
          responses: level1Answers,
          level: 1,
          trigger_final_evaluation: false
        }),
      });
      console.log("✅ Level 1 submitted");
    }

    // Submit Level 2
    const level2Answers = allLevelAnswers.level2;
    if (Object.keys(level2Answers).length > 0) {
      await fetchJson(`${API_BASE_URL}/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          audio_id: levelAudioMap[2] || "level2",
          responses: level2Answers,
          level: 2,
          trigger_final_evaluation: false
        }),
      });
      console.log("✅ Level 2 submitted");
    }

    // Submit Level 3 with final evaluation trigger
    const level3Answers = allLevelAnswers.level3;
    const payload = {
      audio_id: currentAudioId || levelAudioMap[3] || "level3",
      responses: level3Answers,
      level: 3,
      trigger_final_evaluation: triggerFinalEvaluation
    };

    // Final evaluation can take 2–4 minutes (ML models); use 6 min timeout
    const result = await fetchJson(`${API_BASE_URL}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, 360000);

    // Remove loading indicator
    if (loadingIndicator.parentElement) {
      loadingIndicator.remove();
    }

    console.log("📥 Final evaluation response received:", result);
    console.log("📥 Result keys:", Object.keys(result || {}));

    // Validate result object
    if (!result) {
      console.error("❌ Result object is null or undefined!");
      alert("Error: No result received from server. Please try again.");
      el.submitBtn.disabled = false;
      el.submitBtn.textContent = "Submit Answers";
      return;
    }

    // Ensure result has required fields with defaults
    if (result.level === undefined) {
      result.level = 3;
    }
    if (result.score === undefined) {
      result.score = 0;
    }
    if (result.total === undefined) {
      result.total = 0;
    }
    if (result.details === undefined) {
      result.details = {};
    }

    console.log("📊 Processed result:", {
      level: result.level,
      score: result.score,
      total: result.total,
      hasDetails: !!result.details,
      detailsKeys: Object.keys(result.details || {})
    });

    // Store evaluation result
    const summaryData = {
      overall_accuracy: result.overall_accuracy || result.accuracy || 0,
      overall_precision: result.overall_precision || result.precision || 0,
      overall_answer_relevance: result.overall_answer_relevance || result.answer_relevance || 0,
      final_listening_score: result.final_listening_score || result.overall_score || 0,
      level: result.level || 3,
      score: result.score || 0,
      total: result.total || 0,
      accuracy: result.accuracy || 0,
      pass: result.pass !== undefined ? result.pass : false
    };

    localStorage.setItem('lastEvaluationResult', JSON.stringify(summaryData));
    // Store for assessment flow so it can show listening results and continue to Speaking
    try {
      const flowResult = {
        level_results: result.level_results,
        overall_score: result.overall_score ?? result.final_listening_score,
        accuracy: result.accuracy,
        final_listening_score: result.final_listening_score ?? result.overall_score,
        score: result.score,
        total: result.total,
        pass: result.pass
      };
      localStorage.setItem('listeningResults', JSON.stringify(flowResult));
      sessionStorage.setItem('listeningResults', JSON.stringify(flowResult));
    } catch (e) { console.warn('Could not store listeningResults for flow', e); }
    console.log("💾 Evaluation summary data stored");

    // NOW show results (only after all 3 levels completed and evaluation done)
    if (!el.resultCard) {
      console.log("⚠️ Result card not found, re-initializing elements...");
      initializeElements();
      if (!el.resultCard) {
        console.error("❌ Result card still not found after re-initialization!");
        alert("Error: Result card element not found. Please refresh the page.");
        el.submitBtn.disabled = false;
        el.submitBtn.textContent = "Submit Answers";
        return;
      }
    }

    try {
      el.resultCard.style.display = "block";
      el.resultCard.style.visibility = "visible";
      el.resultCard.style.opacity = "1";

      console.log("📊 Calling showResult with:", result);
      showResult(result);
      console.log("✅ showResult completed successfully");

      // Backend returned evaluation – always show result page and "Continue with Speaking" when passed
      if (triggerFinalEvaluation && result) {
        console.log("🎯 Showing result page and Continue with Speaking...", { hasLevelResults: !!(result.level_results && result.level_results.length) });
        try {
          localStorage.setItem('listeningResults', JSON.stringify(result));
          sessionStorage.setItem('listeningResults', JSON.stringify(result));
        } catch (e) { console.warn('Could not store listeningResults', e); }
        try {
          if (result.level_results && result.level_results.length > 0) {
            var overallResultsSection = document.createElement('div');
            overallResultsSection.id = 'overall-results-section';
            overallResultsSection.style.cssText = 'margin-top: 24px; padding: 20px; background: #f8f9fa; border-radius: 12px; border: 2px solid #dee2e6;';
            el.resultDetails.appendChild(overallResultsSection);
            renderOverallResults(overallResultsSection, result);
            var reportBottom = document.createElement('div');
            el.resultDetails.appendChild(reportBottom);
            renderEvaluationReportBottom(reportBottom, result);
          } else {
            var simpleScore = document.createElement('div');
            simpleScore.style.cssText = 'margin-top: 24px; padding: 24px; background: #f8f9fa; border-radius: 12px; border: 2px solid #dee2e6;';
            var overallPct = result.overall_score != null ? (result.overall_score <= 1 ? result.overall_score * 100 : result.overall_score) : (result.final_listening_score != null ? (result.final_listening_score <= 1 ? result.final_listening_score * 100 : result.final_listening_score) : 0);
            simpleScore.innerHTML = '<h3 style="margin:0 0 12px 0; font-size:1.2em;">Final Score</h3><p style="font-size:2em; font-weight:700; margin:0;">' + Number(overallPct).toFixed(1) + '%</p><p style="margin:8px 0 0 0; color:#666;">Learner Level: ' + (result.learner_level || '—') + '</p>';
            el.resultDetails.appendChild(simpleScore);
          }
          appendContinueToNextTestButton();
        } catch (err) {
          console.error('Error rendering overall results:', err);
          appendContinueToNextTestButton();
        }
        if (el.resultCard) {
          el.resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    } catch (err) {
      console.error("❌ Error in showResult:", err);
      console.error("Error stack:", err.stack);
      alert(`Error displaying results: ${err.message}\n\nPlease check the browser console for details.`);
      el.submitBtn.disabled = false;
      el.submitBtn.textContent = "Submit Answers";
      return;
    }

    console.log("✅ Final evaluation completed and results displayed");
  } catch (err) {
    // Remove loading indicator on error
    const loadingIndicator = document.getElementById('evaluation-loading');
    if (loadingIndicator && loadingIndicator.parentElement) {
      loadingIndicator.remove();
    }

    console.error("Submit error:", err);
    console.error("Error details:", err.stack);
    let errorMessage = err.message || "Unknown error";
    if (errorMessage.includes("timeout")) {
      errorMessage = "Evaluation is taking longer than expected. The server may be processing ML models. Please wait and try again, or check the server console for progress.";
    }
    alert(`Error submitting answers: ${errorMessage}\n\nIf this keeps happening, check that the server is running (python Backend/app.py) and check the server console for errors.`);
  } finally {
    el.submitBtn.disabled = false;
    el.submitBtn.textContent = "Submit Answers";

    // Ensure loading indicator is removed
    const loadingIndicator = document.getElementById('evaluation-loading');
    if (loadingIndicator && loadingIndicator.parentElement) {
      loadingIndicator.remove();
    }
  }
}

function setupEvents() {
  el.levelBtns.forEach((btn) => {
    btn.addEventListener("click", () => loadLevel(Number(btn.dataset.level)));
  });
  el.submitBtn.addEventListener("click", submitAnswers);

  if (el.nextLevelBtn) {
    el.nextLevelBtn.addEventListener("click", () => {
      if (currentLevel < 3) {
        loadLevel(currentLevel + 1);
      }
    });
  }
}

// Drag and drop functionality for ordering questions
// Global timer countdown function
// Auto-submit all incomplete levels when time expires
async function autoSubmitAllLevels() {
  console.log('🚨 Auto-submitting all incomplete levels due to time expiration...');

  // Disable all form inputs
  const allInputs = document.querySelectorAll('input, textarea, select');
  allInputs.forEach(input => {
    input.disabled = true;
  });

  // Disable submit button
  if (el.submitBtn) {
    el.submitBtn.disabled = true;
    el.submitBtn.textContent = 'Time Expired - Submitting...';
  }

  // Submit current level if not already submitted
  const level1Completed = localStorage.getItem('level_1_completed') === 'true';
  const level2Completed = localStorage.getItem('level_2_completed') === 'true';
  const level3Completed = localStorage.getItem('level_3_completed') === 'true';

  // Submit Level 1 if not completed
  if (!level1Completed) {
    console.log('📤 Auto-submitting Level 1...');
    try {
      const savedLevel = currentLevel;
      currentLevel = 1;
      await submitAnswersForLevel(1);
      currentLevel = savedLevel;
    } catch (err) {
      console.error('Error auto-submitting Level 1:', err);
    }
  }

  // Submit Level 2 if not completed
  if (!level2Completed) {
    console.log('📤 Auto-submitting Level 2...');
    try {
      const savedLevel = currentLevel;
      currentLevel = 2;
      await submitAnswersForLevel(2);
      currentLevel = savedLevel;
    } catch (err) {
      console.error('Error auto-submitting Level 2:', err);
    }
  }

  // Submit Level 3 if not completed
  if (!level3Completed) {
    console.log('📤 Auto-submitting Level 3...');
    try {
      const savedLevel = currentLevel;
      currentLevel = 3;
      await submitAnswersForLevel(3);
      currentLevel = savedLevel;
    } catch (err) {
      console.error('Error auto-submitting Level 3:', err);
    }
  }

  // Wait a bit for all submissions to complete, then show final results
  setTimeout(async () => {
    try {
      // Fetch final evaluation results
      const finalResult = await fetchFinalEvaluation();

      // Show results page
      showFinalResultsPage(finalResult);
    } catch (err) {
      console.error('Error fetching final results:', err);
      // Still show what we have
      showFinalResultsPage(null);
    }
  }, 2000);
}

// Submit answers for a specific level (used for auto-submit)
async function submitAnswersForLevel(level) {
  // Temporarily load the level to get questions structure if not already loaded
  const originalLevel = currentLevel;
  const needsLoad = (currentLevel !== level);

  if (needsLoad) {
    currentLevel = level;
    try {
      await loadLevel(level);
      // Wait a bit for DOM to update
      await new Promise(resolve => setTimeout(resolve, 500));
    } catch (err) {
      console.error(`Error loading level ${level} for auto-submit:`, err);
    }
  }

  // Get audio ID for this level
  let audioId = levelAudioMap[level];
  if (level === 2) {
    audioId = "level2";
  }

  // Collect responses (unanswered will be null/empty, which backend treats as 0)
  const responses = collectResponses();

  // Check if this is level 3 and all levels are completed
  const level1Completed = localStorage.getItem('level_1_completed') === 'true';
  const level2Completed = localStorage.getItem('level_2_completed') === 'true';
  const triggerFinalEvaluation = (level === 3 && level1Completed && level2Completed);

  const payload = {
    audio_id: audioId,
    responses: responses,
    level: level,
    trigger_final_evaluation: triggerFinalEvaluation
  };

  // Mark level as completed
  localStorage.setItem(`level_${level}_completed`, 'true');

  const evalTimeout = triggerFinalEvaluation ? 360000 : 120000;
  try {
    const result = await fetchJson(`${API_BASE_URL}/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }, evalTimeout);

    console.log(`✅ Level ${level} auto-submitted:`, result);
    if (needsLoad) {
      currentLevel = originalLevel;
    }
    return result;
  } catch (err) {
    console.error(`❌ Error auto-submitting level ${level}:`, err);
    if (needsLoad) {
      currentLevel = originalLevel;
    }
    throw err;
  }
}

// Show final results page
function showFinalResultsPage(finalResult) {
  // Store final results
  if (finalResult) {
    localStorage.setItem('finalTestResults', JSON.stringify(finalResult));
    try {
      localStorage.setItem('listeningResults', JSON.stringify(finalResult));
      sessionStorage.setItem('listeningResults', JSON.stringify(finalResult));
    } catch (e) { console.warn('Could not store listeningResults', e); }
  }
  localStorage.setItem('testTimeExpired', 'true');

  // Hide main content
  const examContainer = document.querySelector('.exam-container');
  if (examContainer) {
    examContainer.style.display = 'none';
  }

  // Show results
  if (el.resultCard) {
    el.resultCard.style.display = 'block';
    el.resultCard.style.width = '100%';
    el.resultCard.style.maxWidth = '1200px';
    el.resultCard.style.margin = '0 auto';
    el.resultCard.style.padding = '40px 20px';

    let resultsHTML = `
      <div class="result-inner">
        <h2 style="font-size: 2rem; font-weight: 700; color: #000; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 2px solid rgba(0,0,0,0.06);">
          Final Test Results - Time Expired
        </h2>
        <p style="color: #666; margin-bottom: 32px; font-size: 1.1rem; padding: 16px; background: #fff3cd; border-radius: 8px; border-left: 4px solid #ffc107;">
          ⏰ Your test has been automatically submitted. All unanswered questions were marked as 0.
        </p>
    `;

    if (finalResult && finalResult.level_results && Array.isArray(finalResult.level_results)) {
      finalResult.level_results.forEach(levelResult => {
        const level = levelResult.level;
        const questions = levelResult.questions || [];
        const score = questions.filter(function (q) { return q.status === 'correct'; }).length;
        const total = questions.length;
        const percentage = total > 0 ? ((score / total) * 100).toFixed(1) : 0;

        resultsHTML += `
          <div style="background: #fff; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 24px; margin-bottom: 20px;">
            <h3 style="font-size: 1.5rem; font-weight: 700; color: #000; margin-bottom: 16px;">Level ${level}</h3>
            <p style="font-size: 1.2rem; color: #000; margin-bottom: 8px;">
              Score: <strong>${score}/${total}</strong> (${percentage}%)
            </p>
          </div>
        `;
      });

      if (finalResult.overall_score !== undefined) {
        var overallPct = finalResult.overall_score <= 1 ? finalResult.overall_score * 100 : finalResult.overall_score;
        resultsHTML += `
          <div style="background: #000; color: #fff; border-radius: 12px; padding: 32px; margin-top: 32px; text-align: center;">
            <h3 style="font-size: 1.8rem; font-weight: 700; margin-bottom: 16px;">Overall Score</h3>
            <p style="font-size: 2.5rem; font-weight: 700; margin: 0;">
              ${Number(overallPct).toFixed(1)}%
            </p>
          </div>
        `;
      }
    } else {
      // Fallback: show message if results not available
      resultsHTML += `
        <div style="background: #fff; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 24px; text-align: center;">
          <p style="font-size: 1.1rem; color: #666;">Your test has been submitted. Results are being processed.</p>
        </div>
      `;
    }

    resultsHTML += `</div>`;
    el.resultCard.innerHTML = resultsHTML;

    var inner = el.resultCard.querySelector('.result-inner');
    if (inner) {
      // 1) Append evaluation report (final score from terminal) at bottom
      if (finalResult && finalResult.level_results && finalResult.level_results.length > 0) {
        var reportDiv = document.createElement('div');
        renderEvaluationReportBottom(reportDiv, finalResult);
        inner.appendChild(reportDiv);
      }
      // 2) Then append "Continue with Speaking" at bottom. No pass gate. Dashboard only on speaking result page.
      var btnRow = document.createElement('div');
      btnRow.style.cssText = 'margin-top: 24px;';
      var flowLevel = localStorage.getItem('assessmentLevel') || 'basic';
      var rulesUrl = 'speaking-rules.html?level=' + encodeURIComponent(flowLevel);
      var continueLink = document.createElement('a');
      continueLink.href = rulesUrl;
      continueLink.textContent = 'Continue with Speaking';
      continueLink.className = 'btn-primary';
      continueLink.style.cssText = 'display: inline-block; padding: 14px 28px; text-decoration: none; color: #fff; background: #0a0a0a; border-radius: 8px; font-weight: 600;';
      continueLink.addEventListener('click', function (e) {
        e.preventDefault();
        sessionStorage.setItem('listeningCompleted', 'true');
        try {
          var r = localStorage.getItem('listeningResults');
          if (r) sessionStorage.setItem('listeningResults', r);
        } catch (err) { }
        window.location.href = rulesUrl;
      });
      btnRow.appendChild(continueLink);
      inner.appendChild(btnRow);
    }

    el.resultCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}

function startGlobalTimer() {
  // Clear any existing timer
  if (globalTimerInterval) {
    clearInterval(globalTimerInterval);
  }

  const timerDisplay = document.getElementById('global-timer');
  if (!timerDisplay) {
    console.warn('⚠️ Timer display element not found');
    return;
  }

  function updateTimer() {
    const testEndTime = localStorage.getItem('testEndTime');
    if (!testEndTime) {
      timerDisplay.textContent = '15:00';
      return;
    }

    const endTime = parseInt(testEndTime, 10);
    const now = Date.now();
    const remaining = Math.max(0, endTime - now);

    if (remaining <= 0) {
      timerDisplay.textContent = '00:00';
      timerDisplay.classList.add('expired');
      clearInterval(globalTimerInterval);
      console.log('⏰ Time expired - auto-submitting all levels...');

      // Auto-submit all incomplete levels
      autoSubmitAllLevels();
      return;
    }

    const minutes = Math.floor(remaining / 60000);
    const seconds = Math.floor((remaining % 60000) / 1000);
    timerDisplay.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

    // Add warning class when less than 5 minutes
    if (remaining < 5 * 60 * 1000) {
      timerDisplay.classList.add('warning');
    } else {
      timerDisplay.classList.remove('warning');
    }
  }

  // Update immediately
  updateTimer();

  // Update every second
  globalTimerInterval = setInterval(updateTimer, 1000);
}

function initDragAndDrop(container) {
  let draggedElement = null;

  container.querySelectorAll(".ordering-item").forEach((item) => {
    item.addEventListener("dragstart", function (e) {
      draggedElement = this;
      this.classList.add("dragging");
      e.dataTransfer.effectAllowed = "move";
    });

    item.addEventListener("dragend", function () {
      this.classList.remove("dragging");
      container.querySelectorAll(".ordering-item").forEach(i => {
        i.classList.remove("drag-over");
      });
    });

    item.addEventListener("dragover", function (e) {
      if (e.preventDefault) {
        e.preventDefault();
      }
      e.dataTransfer.dropEffect = "move";
      this.classList.add("drag-over");
      return false;
    });

    item.addEventListener("dragleave", function () {
      this.classList.remove("drag-over");
    });

    item.addEventListener("drop", function (e) {
      if (e.stopPropagation) {
        e.stopPropagation();
      }

      if (draggedElement !== this) {
        const allItems = Array.from(container.querySelectorAll(".ordering-item"));
        const draggedIndex = allItems.indexOf(draggedElement);
        const targetIndex = allItems.indexOf(this);

        if (draggedIndex < targetIndex) {
          container.insertBefore(draggedElement, this.nextSibling);
        } else {
          container.insertBefore(draggedElement, this);
        }

        // Auto-save to localStorage after reordering
        autoSaveAnswers();
      }

      this.classList.remove("drag-over");
      return false;
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  console.log("🚀 DOM Content Loaded - Initializing Tamil Listening Module...");
  console.log("⏰ Time:", new Date().toISOString());

  // On page load/refresh: clear all test state and answers so user gets a fresh assessment
  console.log("🔄 Clearing test state and answers for fresh start...");
  localStorage.removeItem('testStarted');
  localStorage.removeItem('testStartTime');
  localStorage.removeItem('testEndTime');
  localStorage.removeItem('currentTestLevel');
  localStorage.removeItem('level_1_completed');
  localStorage.removeItem('level_2_completed');
  localStorage.removeItem('level_3_completed');
  localStorage.removeItem('level_1_answers');
  localStorage.removeItem('level_2_answers');
  localStorage.removeItem('level_3_answers');
  localStorage.removeItem('audio_play_count_level_1');
  localStorage.removeItem('audio_play_count_level_2');
  localStorage.removeItem('audio_play_count_level_3');
  localStorage.removeItem('finalTestResults');
  localStorage.removeItem('testTimeExpired');
  localStorage.removeItem('lastEvaluationResult');
  localStorage.removeItem('listeningResults');
  console.log("✅ Test state and answers cleared – fresh assessment");

  // Parse URL parameter for level
  const urlParams = new URLSearchParams(window.location.search);
  const urlLevel = urlParams.get('level');
  if (urlLevel) {
    const parsedLevel = parseInt(urlLevel, 10);
    if (!isNaN(parsedLevel) && parsedLevel >= 1 && parsedLevel <= 3) {
      currentLevel = parsedLevel;
      console.log(`📍 Level from URL parameter: ${currentLevel}`);
    } else {
      currentLevel = 1;
    }
  } else {
    currentLevel = 1;
  }
  var assessmentLevel = urlParams.get('assessmentLevel');
  if (assessmentLevel) {
    localStorage.setItem('assessmentLevel', assessmentLevel);
    console.log('📍 Assessment level from URL:', assessmentLevel);
  }

  // Auto-start test (always start fresh)
  console.log('🚀 Starting new test...');
  localStorage.setItem('testStarted', 'true');
  const testStartTime = Date.now();
  localStorage.setItem('testStartTime', testStartTime.toString());

  // Initialize global test timer: 15 minutes = 900000 ms
  const testTimeLimit = 15 * 60 * 1000; // 15 minutes in milliseconds
  const testEndTime = testStartTime + testTimeLimit;
  localStorage.setItem('testEndTime', testEndTime.toString());

  // Set test level to 1
  localStorage.setItem('currentTestLevel', '1');
  currentLevel = 1;

  console.log('✅ Test started with 15 minute timer');

  // Initialize global test timer
  remainingGlobalTestTime = testTimeLimit;

  console.log('⏱️ Global test timer initialized:');
  console.log('   Start time:', new Date(testStartTime).toISOString());
  console.log('   End time:', new Date(testEndTime).toISOString());
  console.log('   Remaining time:', Math.floor(remainingGlobalTestTime / 60000), 'minutes');

  // Start timer countdown
  startGlobalTimer();

  // Initialize elements first
  initializeElements();

  // Check if all required elements exist
  const missingElements = [];
  if (!el.audioPlayer) missingElements.push("audioPlayer");
  if (!el.questions) missingElements.push("questions");
  if (!el.submitBtn) missingElements.push("submitBtn");

  if (missingElements.length > 0) {
    console.error("❌ Missing required elements:", missingElements);
    const questionsEl = document.getElementById("questions-container");
    if (questionsEl) {
      questionsEl.innerHTML = `<div style='color:#c0392b; padding: 20px; border: 2px solid #c0392b; border-radius: 8px; background: #ffe6e6;'>
        <strong>⚠️ Error: Page elements not found.</strong><br>
        Missing: ${missingElements.join(", ")}<br>
        <small>Please refresh the page (Ctrl+F5 for hard refresh).</small><br>
        <button onclick='location.reload()' style='margin-top: 10px; padding: 8px 16px; background: #c0392b; color: white; border: none; border-radius: 4px; cursor: pointer;'>Reload Page</button>
      </div>`;
    }
    return;
  }

  console.log("✅ All required elements found");
  console.log("📋 Setting up events...");
  setupEvents();
  console.log("📥 Loading initial level...");
  console.log("📍 Current level from URL:", currentLevel);

  // Update localStorage with current level
  localStorage.setItem('currentTestLevel', currentLevel.toString());

  // Add a small delay to ensure everything is ready
  setTimeout(() => {
    loadLevel(currentLevel);
  }, 100);
});

