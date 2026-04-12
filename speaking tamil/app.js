// MODULE 1: Conversation Orchestrator (HTML + JS implementation)

const SessionState = {
  INIT: "INIT",
  AVATAR_SPEAKING: "AVATAR_SPEAKING",
  USER_SPEAKING: "USER_SPEAKING",
  PROCESSING: "PROCESSING",
  WAITING_NEXT: "WAITING_NEXT",
  END: "END",
};

// Backend (FastAPI) base URL for STEP 4/5
const API_BASE_URL = "http://127.0.0.1:8001";

// Assessment flow: level from URL (e.g. ?level=intermediate) – only intermediate gets "Continue with Reading"
const flowLevel = (function () {
  var p = new URLSearchParams(window.location.search);
  return (p.get("level") || "").toLowerCase();
})();

// Central single source of truth for the conversation
const conversationState = {
  currentState: SessionState.INIT,
  currentQuestionIndex: 0,
  questions: [
    {
      id: 1,
      level: "basic",
      text: "திரைப்படங்களை பார்ப்பது பற்றி உங்கள் கருத்து என்ன?",
      timeLimitSec: 75,
    },
    {
      id: 2,
      level: "mid",
      text: "நீங்கள் ஒரு புதிய இடத்திற்கு சென்றால் எப்படி அங்குள்ள மக்களுடன் பழகுவீர்கள்?",
      timeLimitSec: 90,
    },
    {
      id: 3,
      level: "final",
      text: "நேர மேலாண்மை வாழ்க்கையில் எவ்வளவு முக்கியம் என்பதை எடுத்துக்காட்டுடன் சொல்லுங்கள்.",
      timeLimitSec: 120,
    },
  ],
  recordings: [],
  assessments: [], // per questionIndex: response from /api/assess-answer
  timers: {
    question: null,
    global: null,
  },
  questionTimeLeftSec: 0,
  globalTimeLeftSec: 10 * 60, // 10 minutes
  globalTimerPaused: false, // Track if global timer is paused
  levelStatus: {
    1: "locked", // locked, available, completed, skipped
    2: "locked",
    3: "locked",
  },
  isMicOn: false,
  repeatUsed: {}, // questionIndex -> count (max 2 repeats allowed)
};

// STEP 3: User Speech Capture (microphone + recording)
let mediaStream = null;
let mediaRecorder = null;
let audioChunks = [];
let recordingStartedAtMs = null;
let assessTimeoutId = null;
let assessAbortController = null;
let micPermissionGranted = false;

// Live captions (browser STT) for UI only
let speechRecognition = null;
let finalTranscript = "";

// Global AbortController for TTS fetches
let ttsAbortController = null;

const elements = {
  testPage: document.getElementById("test-page"),
  resultsPage: document.getElementById("results-page"),
  stateLabel: document.getElementById("state-label"),
  questionIndex: document.getElementById("question-index"),
  questionTimer: document.getElementById("question-timer"),
  questionText: document.getElementById("question-text"),
  liveTranscript: document.getElementById("live-transcript"),
  resultText: document.getElementById("result-text"),
  playRepeatQuestionBtn: document.getElementById("play-repeat-question-btn"),
  micToggleBtn: document.getElementById("mic-toggle-btn"),
  avatar: document.getElementById("avatar"),
  avatarLabel: document.getElementById("avatar-label"),
  speechBubble: document.getElementById("speech-bubble"),
  speechText: document.getElementById("speech-text"),
  questionProgress: document.getElementById("question-progress"),
  testSubtitle: document.getElementById("test-subtitle"),
  resultStatusText: document.getElementById("result-status-text"),
  resultMarksText: document.getElementById("result-marks-text"),
  resultPercentage: document.getElementById("result-percentage"),
  detailedResults: document.getElementById("detailed-results"),
  globalTimer: document.getElementById("global-timer"),
  level1Btn: document.getElementById("level-1-btn"),
  level2Btn: document.getElementById("level-2-btn"),
  level3Btn: document.getElementById("level-3-btn"),
  skipLevelBtn: document.getElementById("skip-level-btn"),
  nextLevelBtn: document.getElementById("next-level-btn"),
};

// MODULE 2: Virtual Interviewer Avatar Renderer
const AvatarRenderer = {
  setSpeaking(questionText) {
    if (elements.avatar) {
      elements.avatar.classList.add("avatar-speaking");
      elements.avatar.classList.remove("avatar-idle");
    }
    if (elements.avatarLabel) elements.avatarLabel.textContent = "Asking";
    if (typeof questionText === "string") {
      if (elements.speechText) elements.speechText.textContent = questionText;
      if (elements.speechBubble) elements.speechBubble.classList.remove("hidden");
    }
  },
  setIdle() {
    if (elements.avatar) {
      elements.avatar.classList.remove("avatar-speaking");
      elements.avatar.classList.add("avatar-idle");
    }
    if (elements.avatarLabel) elements.avatarLabel.textContent = "Listening";
    if (elements.speechBubble) elements.speechBubble.classList.add("hidden");
  },
};

function formatTime(sec) {
  const minutes = Math.floor(sec / 60);
  const seconds = sec % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(
    2,
    "0"
  )}`;
}

function showView(view) {
  // Hide all pages
  elements.testPage?.classList.add("hidden");
  elements.resultsPage?.classList.add("hidden");

  // Show requested page
  if (view === "test") {
    elements.testPage?.classList.remove("hidden");
  } else if (view === "results") {
    elements.resultsPage?.classList.remove("hidden");
  }
}

function updateUI() {
  const state = conversationState;

  // Update level buttons
  updateLevelButtons();

  if (state.currentQuestionIndex < 0) {
    if (elements.questionText) elements.questionText.textContent = 'Loading question...';
  } else if (state.currentQuestionIndex < state.questions.length) {
    const q = state.questions[state.currentQuestionIndex];
    if (elements.questionText) elements.questionText.textContent = q.text;

    // Show/hide hint based on TTS unlock status
    const questionHint = document.getElementById("question-hint");
    if (questionHint) {
      if (!ttsUnlocked && state.currentState === SessionState.AVATAR_SPEAKING) {
        questionHint.style.display = "block";
        questionHint.textContent = "⚠️ Click anywhere on the page or click 'Play Question' button to hear the question";
      } else {
        questionHint.style.display = "none";
      }
    }
  } else {
    // All questions completed
    const questionHint = document.getElementById("question-hint");
    if (questionHint) questionHint.style.display = "none";
  }

  // Live transcript UI
  if (elements.liveTranscript) {
    if (state.currentState === SessionState.USER_SPEAKING) {
      if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
        elements.liveTranscript.textContent =
          "Live transcript not supported in this browser. Use Chrome / Edge.";
      } else if (state.isMicOn) {
        // leave current transcript content
        if (!elements.liveTranscript.textContent.trim()) {
          elements.liveTranscript.textContent = "Listening…";
        }
      } else {
        elements.liveTranscript.textContent =
          "Press \"Start Mic\" and speak to see live captions…";
      }
    } else if (state.currentState === SessionState.PROCESSING || state.currentState === SessionState.WAITING_NEXT) {
      // keep last transcript visible
    } else {
      elements.liveTranscript.textContent =
        "Press \"Start Mic\" and speak to see live captions…";
    }
  }

  // Result box
  if (state.currentState === SessionState.PROCESSING) {
    if (elements.resultText) {
      elements.resultText.textContent = "Analyzing your speech... This might take a minute on first run.";
      elements.resultText.style.color = "var(--primary-color)";
    }
    // Show a manual skip/next button if it takes too long
    if (elements.nextLevelBtn) {
      elements.nextLevelBtn.style.display = "inline-block";
      elements.nextLevelBtn.textContent = "Force Next Question (if stuck)";
      elements.nextLevelBtn.disabled = false;
    }
  } else if (state.currentState === SessionState.END) {
    // Show results page
    showResultsPage();
  } else if (
    typeof state.currentQuestionIndex === "number" &&
    state.currentQuestionIndex >= 0
  ) {
    if (elements.resultText && state.currentState !== SessionState.WAITING_NEXT) {
      elements.resultText.textContent = "Record your answer to see the result.";
      elements.resultText.style.color = "inherit";
    }
    if (elements.nextLevelBtn && state.currentState !== SessionState.WAITING_NEXT) {
      elements.nextLevelBtn.style.display = "none";
    }
  }

  // Show Next button ONLY in WAITING_NEXT state
  if (state.currentState === SessionState.WAITING_NEXT) {
    if (elements.nextLevelBtn) {
      elements.nextLevelBtn.style.display = "inline-block";
      elements.nextLevelBtn.textContent = "Next Question";
      elements.nextLevelBtn.disabled = false;
    }
  }

  // Drive avatar purely from orchestrator state
  if (
    state.currentState === SessionState.AVATAR_SPEAKING &&
    state.currentQuestionIndex >= 0 &&
    state.currentQuestionIndex < state.questions.length
  ) {
    const q = state.questions[state.currentQuestionIndex];
    AvatarRenderer.setSpeaking(q.text);
  } else {
    AvatarRenderer.setIdle();
  }

  // Combined Play/Repeat Question button
  if (elements.playRepeatQuestionBtn) {
    const canPlay = state.currentState === SessionState.AVATAR_SPEAKING ||
      state.currentState === SessionState.USER_SPEAKING;
    const repeatCount = state.repeatUsed[state.currentQuestionIndex] || 0;
    const maxRepeats = 2;
    const canRepeat = state.currentState === SessionState.USER_SPEAKING &&
      !state.isMicOn &&
      state.currentQuestionIndex >= 0 &&
      state.currentQuestionIndex < state.questions.length &&
      repeatCount < maxRepeats;

    if (canPlay) {
      elements.playRepeatQuestionBtn.disabled = false;
      // Show "Play Question" if not repeated yet, or "Repeat Question (X/2)" if repeated
      if (repeatCount === 0) {
        elements.playRepeatQuestionBtn.textContent = "Play Question";
      } else {
        elements.playRepeatQuestionBtn.textContent = `Repeat Question (${repeatCount}/${maxRepeats})`;
      }
      // Disable if max repeats reached
      if (repeatCount >= maxRepeats) {
        elements.playRepeatQuestionBtn.disabled = true;
        elements.playRepeatQuestionBtn.textContent = `Repeat Question (${maxRepeats}/${maxRepeats} used)`;
      }
      elements.playRepeatQuestionBtn.style.pointerEvents = "auto";
      elements.playRepeatQuestionBtn.style.cursor = "pointer";
    } else {
      elements.playRepeatQuestionBtn.disabled = true;
    }
  }

  // Combined Mic Toggle button (Start Mic / Next)
  if (elements.micToggleBtn) {
    const canUseMicPhase = state.currentState === SessionState.USER_SPEAKING;
    if (state.isMicOn) {
      // Show "Next" when recording - clicking will process and move to next question
      elements.micToggleBtn.textContent = "Next";
      elements.micToggleBtn.disabled = !canUseMicPhase;
    } else {
      // Show "Start Mic" when not recording
      elements.micToggleBtn.textContent = "Start Mic";
      elements.micToggleBtn.disabled = !canUseMicPhase;
    }
    elements.micToggleBtn.style.pointerEvents = elements.micToggleBtn.disabled ? "none" : "auto";
    elements.micToggleBtn.style.cursor = elements.micToggleBtn.disabled ? "not-allowed" : "pointer";
  }

  // Ensure skip and next level buttons are clickable when enabled
  if (elements.skipLevelBtn && !elements.skipLevelBtn.disabled) {
    elements.skipLevelBtn.style.pointerEvents = "auto";
    elements.skipLevelBtn.style.cursor = "pointer";
  }
  if (elements.nextLevelBtn && !elements.nextLevelBtn.disabled) {
    elements.nextLevelBtn.style.pointerEvents = "auto";
    elements.nextLevelBtn.style.cursor = "pointer";
  }


  // Skip Level button - only available when not recording and level is available
  const currentLevel = state.currentQuestionIndex + 1;
  const canSkip =
    state.currentState === SessionState.USER_SPEAKING &&
    !state.isMicOn &&
    state.currentQuestionIndex >= 0 &&
    state.currentQuestionIndex < state.questions.length &&
    state.levelStatus[currentLevel] === "available";
  if (elements.skipLevelBtn) {
    elements.skipLevelBtn.disabled = !canSkip;
  }

  // Next Level button logic for WAITING_NEXT is handled above.
}

function clearTimers() {
  if (conversationState.timers.question) {
    clearInterval(conversationState.timers.question);
    conversationState.timers.question = null;
  }
  if (conversationState.timers.global) {
    clearInterval(conversationState.timers.global);
    conversationState.timers.global = null;
  }
}

function startGlobalTimer() {
  conversationState.globalTimeLeftSec = 10 * 60; // 10 minutes
  conversationState.globalTimerPaused = false; // Track if timer is paused
  if (conversationState.timers.global) {
    clearInterval(conversationState.timers.global);
  }
  conversationState.timers.global = setInterval(() => {
    // Don't decrement if timer is paused
    if (conversationState.globalTimerPaused) {
      return;
    }

    if (conversationState.globalTimeLeftSec <= 0) {
      conversationState.globalTimeLeftSec = 0;
      if (elements.globalTimer) {
        elements.globalTimer.textContent = "00:00";
        elements.globalTimer.classList.add("expired");
      }
      return;
    }
    conversationState.globalTimeLeftSec -= 1;
    if (elements.globalTimer) {
      const minutes = Math.floor(conversationState.globalTimeLeftSec / 60);
      const seconds = conversationState.globalTimeLeftSec % 60;
      elements.globalTimer.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

      // Add warning class when less than 5 minutes
      if (conversationState.globalTimeLeftSec < 300) {
        elements.globalTimer.classList.add("warning");
      } else {
        elements.globalTimer.classList.remove("warning");
      }

      // Add expired class when time is up
      if (conversationState.globalTimeLeftSec === 0) {
        elements.globalTimer.classList.add("expired");
      } else {
        elements.globalTimer.classList.remove("expired");
      }
    }
  }, 1000);
}

function pauseGlobalTimer() {
  conversationState.globalTimerPaused = true;
}

function resumeGlobalTimer() {
  conversationState.globalTimerPaused = false;
}

function updateLevelButtons() {
  const state = conversationState;
  const currentLevel = state.currentQuestionIndex + 1;
  const levelStatus = state.levelStatus;

  // Update Level 1 button
  if (elements.level1Btn) {
    if (levelStatus[1] === "locked") {
      elements.level1Btn.disabled = true;
      elements.level1Btn.classList.remove("active");
    } else if (levelStatus[1] === "available" || levelStatus[1] === "completed" || levelStatus[1] === "skipped") {
      elements.level1Btn.disabled = false;
      elements.level1Btn.classList.toggle("active", currentLevel === 1);
    }
  }

  // Update Level 2 button - only available if Level 1 is completed or skipped
  if (elements.level2Btn) {
    if (levelStatus[1] === "locked" || levelStatus[1] === "available") {
      elements.level2Btn.disabled = true;
      elements.level2Btn.classList.remove("active");
    } else if (levelStatus[1] === "completed" || levelStatus[1] === "skipped") {
      elements.level2Btn.disabled = false;
      elements.level2Btn.classList.toggle("active", currentLevel === 2);
    }
  }

  // Update Level 3 button - only available if Level 2 is completed or skipped
  if (elements.level3Btn) {
    if (levelStatus[2] === "locked" || levelStatus[2] === "available") {
      elements.level3Btn.disabled = true;
      elements.level3Btn.classList.remove("active");
    } else if (levelStatus[2] === "completed" || levelStatus[2] === "skipped") {
      elements.level3Btn.disabled = false;
      elements.level3Btn.classList.toggle("active", currentLevel === 3);
    }
  }
}

function clearAssessTimeout() {
  if (assessTimeoutId) {
    clearTimeout(assessTimeoutId);
    assessTimeoutId = null;
  }
  if (assessAbortController) {
    try {
      assessAbortController.abort();
    } catch (_) { }
    assessAbortController = null;
  }
}

let currentUtterance = null;
let currentAudioElement = null; // Track current audio element from API TTS
let isTTSPlaying = false; // Flag to prevent multiple TTS from playing simultaneously

// TTS unlock flag
let ttsUnlocked = false;

// Best Tamil voice found
let bestTamilVoice = null;

// Find the best Tamil voice available
function findBestTamilVoice() {
  if (!window.speechSynthesis) return null;

  const voices = window.speechSynthesis.getVoices();
  console.log("🔍 Available voices:", voices.length);

  // Priority order for Tamil voices
  const tamilVoicePatterns = [
    /tamil/i,
    /ta[-_]in/i,
    /india/i,
    /indian/i,
  ];

  // First, try to find a voice with "Tamil" in the name
  for (const pattern of tamilVoicePatterns) {
    for (const voice of voices) {
      if (pattern.test(voice.name) || pattern.test(voice.lang)) {
        console.log("✅ Found Tamil voice:", voice.name, voice.lang);
        return voice;
      }
    }
  }

  // Fallback: find any voice with ta-IN or ta language code
  for (const voice of voices) {
    if (voice.lang.startsWith("ta")) {
      console.log("✅ Found Tamil language voice:", voice.name, voice.lang);
      return voice;
    }
  }

  // Last resort: use default voice but set language to ta-IN
  console.log("⚠️ No Tamil voice found, using default with ta-IN language");
  return null;
}

// Load voices (they may not be available immediately)
function loadVoices() {
  if (!window.speechSynthesis) return;

  const voices = window.speechSynthesis.getVoices();
  if (voices.length > 0) {
    bestTamilVoice = findBestTamilVoice();
  } else {
    // Voices may load asynchronously
    window.speechSynthesis.onvoiceschanged = () => {
      bestTamilVoice = findBestTamilVoice();
    };
  }
}

// TTS engine for avatar; not aware of global FSM, only uses callback
async function speakQuestion(text, { notifyOnEnd } = { notifyOnEnd: true }) {
  console.log("🔊 speakQuestion called with text:", text);

  // 1. Cancel any ongoing TTS work immediately
  stopAllTTS();

  // 2. Clear state
  isTTSPlaying = true; // Mark as busy immediately to prevent other calls

  try {
    // 3. Try API TTS
    await useTamilTTSAPI(text, notifyOnEnd);
  } catch (error) {
    if (error.name === 'AbortError') {
      console.log("🚫 TTS API call was aborted.");
      return;
    }

    // 4. Fallback to Browser TTS
    console.log("🔄 API TTS failed, using browser fallback:", error);
    isTTSPlaying = false; // Reset to allow browser fallback to start
    useBrowserTTS(text, notifyOnEnd);
  }
}

// Stop all TTS (both API audio and browser TTS)
function stopAllTTS() {
  isTTSPlaying = false;

  // Abort any ongoing fetch
  if (ttsAbortController) {
    ttsAbortController.abort();
    ttsAbortController = null;
  }

  // Stop browser TTS
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  // Stop API audio element
  if (currentAudioElement) {
    try {
      currentAudioElement.pause();
      currentAudioElement.onended = null;
      currentAudioElement.onerror = null;
      currentAudioElement.currentTime = 0;
      if (currentAudioElement.src) {
        URL.revokeObjectURL(currentAudioElement.src);
      }
    } catch (e) {
      console.warn("Error stopping audio element:", e);
    }
    currentAudioElement = null;
  }

  currentUtterance = null;
}

// Use Tamil TTS API (backend service)
async function useTamilTTSAPI(text, notifyOnEnd) {
  // Make sure browser TTS is stopped before using API
  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  // Set up cancellation
  ttsAbortController = new AbortController();
  const signal = ttsAbortController.signal;

  try {
    const response = await fetch(`${API_BASE_URL}/api/tts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ text: text, language: "ta-IN" }),
      signal: signal
    });

    if (!response.ok) {
      throw new Error("TTS API not available");
    }

    const audioBlob = await response.blob();
    if (signal.aborted) return;

    const audioUrl = URL.createObjectURL(audioBlob);
    const audio = new Audio(audioUrl);

    // Store reference to current audio element
    currentAudioElement = audio;
    isTTSPlaying = true;

    return new Promise((resolve, reject) => {
      audio.onplay = () => {
        pauseGlobalTimer();
      };

      audio.onended = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudioElement = null;
        isTTSPlaying = false;
        resumeGlobalTimer();
        if (notifyOnEnd) onAvatarAudioEnded();
        resolve();
      };

      audio.onpause = () => {
        resumeGlobalTimer();
      };

      audio.onerror = () => {
        URL.revokeObjectURL(audioUrl);
        currentAudioElement = null;
        isTTSPlaying = false;
        resumeGlobalTimer();
        console.error("Audio playback failed");
        if (notifyOnEnd) onAvatarAudioEnded();
        reject(new Error("Audio playback failed"));
      };

      console.log("✅ Using Tamil TTS API");
      audio.play().catch(reject);
    });
  } catch (error) {
    if (error.name !== 'AbortError') {
      isTTSPlaying = false;
      console.log("⚠️ TTS API error:", error);
    }
    throw error;
  }
}

// Use browser TTS with best available Tamil voice
function useBrowserTTS(text, notifyOnEnd) {
  // Prevent multiple TTS from playing
  if (isTTSPlaying) {
    console.log("⚠️ TTS already playing, skipping browser TTS");
    return;
  }

  // Make sure API audio is stopped before using browser TTS
  if (currentAudioElement) {
    try {
      currentAudioElement.pause();
      currentAudioElement.currentTime = 0;
      if (currentAudioElement.src) {
        URL.revokeObjectURL(currentAudioElement.src);
      }
    } catch (e) {
      console.warn("Error stopping audio element:", e);
    }
    currentAudioElement = null;
  }

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  // Reload voices in case they weren't loaded yet
  if (!bestTamilVoice) {
    loadVoices();
  }

  // Wait a bit for cancellation
  setTimeout(() => {
    // Check again if TTS is already playing
    if (isTTSPlaying) {
      console.log("⚠️ TTS started playing during delay, skipping browser TTS");
      return;
    }

    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "ta-IN"; // Tamil language

    // Use the best Tamil voice if found
    if (bestTamilVoice) {
      utter.voice = bestTamilVoice;
      console.log("🎤 Using voice:", bestTamilVoice.name);
    } else {
      console.log("🎤 Using default voice with Tamil language");
    }

    utter.volume = 1.0; // max volume
    utter.rate = 0.85; // slightly slower for natural Tamil speech
    utter.pitch = 1.0;

    isTTSPlaying = true;

    if (notifyOnEnd) {
      utter.onend = () => {
        console.log("✅ Speech ended");
        isTTSPlaying = false;
        // Resume timer when speech ends
        resumeGlobalTimer();
        onAvatarAudioEnded();
      };
      utter.onstart = () => {
        console.log("▶️ Speech started");
        // Pause timer when speech actually starts
        pauseGlobalTimer();
      };
      utter.onerror = (event) => {
        console.error("❌ Speech synthesis error:", event);
        isTTSPlaying = false;
        // Resume timer on error
        resumeGlobalTimer();
        // If TTS fails, still proceed to next state
        if (notifyOnEnd) {
          setTimeout(() => {
            onAvatarAudioEnded();
          }, 1000);
        }
      };
    }

    currentUtterance = utter;

    try {
      console.log("🎤 Attempting to speak...");
      window.speechSynthesis.speak(utter);
      console.log("✅ speak() called successfully");

      // Check if it actually started
      setTimeout(() => {
        if (!window.speechSynthesis.speaking && !window.speechSynthesis.pending) {
          console.warn("⚠️ Speech did not start - may need user interaction");
          isTTSPlaying = false;
          // Resume timer if speech didn't start
          resumeGlobalTimer();
          // If speech didn't start, proceed anyway after delay
          if (notifyOnEnd) {
            setTimeout(onAvatarAudioEnded, 2000);
          }
        }
      }, 500);
    } catch (error) {
      console.error("❌ Failed to speak:", error);
      isTTSPlaying = false;
      // If speak fails, still proceed
      if (notifyOnEnd) {
        setTimeout(onAvatarAudioEnded, 1000);
      }
    }
  }, 200);
}

function startQuestionTimer(limitSec) {
  conversationState.questionTimeLeftSec = limitSec;
  if (conversationState.timers.question) {
    clearInterval(conversationState.timers.question);
  }
  conversationState.timers.question = setInterval(() => {
    if (conversationState.questionTimeLeftSec <= 0) {
      conversationState.questionTimeLeftSec = 0;
      onUserTimeExpired();
      return;
    }
    conversationState.questionTimeLeftSec -= 1;
    updateUI();
  }, 1000);
}

// STEP 3.1: Microphone permission (request once, before Q1)
async function ensureMicPermission() {
  if (mediaStream && micPermissionGranted) return true;
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    micPermissionGranted = true;
    return true;
  } catch (err) {
    micPermissionGranted = false;
    alert(
      "Microphone access is required to take this speaking test.\n" +
      "Please allow mic permission in your browser and try again."
    );
    console.error("Mic permission denied:", err);
    return false;
  }
}

function initSpeechRecognitionIfAvailable() {
  if (speechRecognition) return;
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return;
  const rec = new SR();
  rec.lang = "ta-IN";
  rec.continuous = true;
  rec.interimResults = true;
  rec.maxAlternatives = 1;

  rec.onresult = (event) => {
    let interim = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const res = event.results[i];
      const text = res[0]?.transcript || "";
      if (res.isFinal) {
        finalTranscript += text.trim() + " ";
      } else {
        interim += text;
      }
    }
    const display = (finalTranscript + interim).trim();
    if (elements.liveTranscript) elements.liveTranscript.textContent = display || "Listening…";
  };

  rec.onerror = (e) => {
    console.warn("SpeechRecognition error:", e);
    // Do not break the test if captioning fails
  };

  rec.onend = () => {
    // Sometimes recognition ends by itself; do nothing.
  };

  speechRecognition = rec;
}

function prewarmSpeechRecognitionPermission() {
  // Goal: if the browser triggers a separate permission for SpeechRecognition,
  // do it once at "Start Test" time (user gesture), not later during questions.
  initSpeechRecognitionIfAvailable();
  if (!speechRecognition) return;
  try {
    speechRecognition.start();
    setTimeout(() => {
      try {
        speechRecognition.stop();
      } catch (_) { }
      // Reset transcript prompt text after warmup
      if (elements.liveTranscript) {
        elements.liveTranscript.textContent =
          'Press "Start Mic" and speak to see live captions…';
      }
    }, 300);
  } catch (e) {
    // Ignore "already started" / "not allowed" errors — warmup is best-effort.
  }
}

function startLiveTranscript() {
  initSpeechRecognitionIfAvailable();
  if (!speechRecognition) return;
  finalTranscript = "";
  if (elements.liveTranscript) elements.liveTranscript.textContent = "Listening…";
  try {
    speechRecognition.start();
  } catch (e) {
    // start() throws if already started; ignore
  }
}

function stopLiveTranscript() {
  if (!speechRecognition) return;
  try {
    speechRecognition.stop();
  } catch (e) {
    // ignore
  }
}

// STEP 3.2–3.5: Recording lifecycle & packaging
function setupMediaRecorderIfNeeded() {
  if (!mediaStream) return;
  if (mediaRecorder) return;
  mediaRecorder = new MediaRecorder(mediaStream);
  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };
  mediaRecorder.onstop = () => {
    const blob = new Blob(audioChunks, { type: mediaRecorder.mimeType });
    audioChunks = [];
    const durationSec = recordingStartedAtMs
      ? (Date.now() - recordingStartedAtMs) / 1000
      : null;
    handleRecordingComplete(blob, durationSec);
  };
}

function startRecordingForCurrentQuestion() {
  if (!mediaStream) return;
  setupMediaRecorderIfNeeded();
  if (!mediaRecorder) return;

  audioChunks = [];
  recordingStartedAtMs = Date.now();
  try {
    mediaRecorder.start();
  } catch (e) {
    console.error("Failed to start recording:", e);
  }
}

function stopRecordingForCurrentQuestion() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    try {
      mediaRecorder.stop();
    } catch (e) {
      console.error("Failed to stop recording:", e);
    }
  }
}

function handleRecordingComplete(blob, durationSec) {
  const questionIndex = conversationState.currentQuestionIndex;
  const minDurationSec = 2; // Reduced from 5
  const minSizeBytes = 1000; // Reduced from 5000

  const isLongEnough =
    typeof durationSec === "number" && durationSec >= minDurationSec;
  const isBigEnough = blob.size >= minSizeBytes;
  const isValid = isLongEnough && isBigEnough;

  const packaged = {
    questionIndex,
    duration: durationSec,
    audioBlob: blob,
    sampleRate: 44100, // approximate; real normalization happens later
    isValid,
  };

  conversationState.recordings.push(packaged);

  // If we are already in PROCESSING state, trigger backend assessment now
  if (conversationState.currentState === SessionState.PROCESSING) {
    assessLatestRecordingAndContinue();
  }
}

async function assessLatestRecordingAndContinue() {
  const state = conversationState;
  const recording = state.recordings[state.recordings.length - 1];
  const q = state.questions[state.currentQuestionIndex];
  const processingQuestionIndex = state.currentQuestionIndex;

  // If step-3 integrity already failed, skip backend call and mark invalid
  if (!recording || !q || recording.isValid === false) {
    state.assessments[state.currentQuestionIndex] = {
      questionIndex: state.currentQuestionIndex,
      transcript: "",
      normalizedTranscript: "",
      wordCount: 0,
      duration: recording?.duration ?? null,
      sttOk: false,
      relevanceOk: false,
      sufficiencyOk: false,
      isValid: false,
      message: "Audio too short / silent. Please speak clearly next time.",
      step5: null,
    };
    onProcessingDone({ success: false, reason: "AUDIO_INVALID" });
    updateUI();
    return;
  }

  const form = new FormData();
  form.append("questionIndex", String(state.currentQuestionIndex));
  form.append("questionText", q.text);
  if (typeof recording.duration === "number") {
    form.append("duration", String(recording.duration));
  }
  form.append(
    "audio",
    recording.audioBlob,
    `q${state.currentQuestionIndex + 1}.webm`
  );

  try {
    clearAssessTimeout();
    assessAbortController = new AbortController();

    // Whisper on CPU can take time. Give it a realistic limit.
    const TIMEOUT_MS = 420000; // 7 minutes
    assessTimeoutId = setTimeout(() => {
      try {
        assessAbortController.abort();
      } catch (_) { }
    }, TIMEOUT_MS);

    const resp = await fetch(`${API_BASE_URL}/api/assess-answer`, {
      method: "POST",
      body: form,
      signal: assessAbortController.signal,
    });
    let data = null;
    try {
      data = await resp.json();
    } catch (_) {
      data = null;
    }

    clearAssessTimeout();

    // If user already moved (shouldn't happen), don't write into wrong slot.
    if (conversationState.currentQuestionIndex !== processingQuestionIndex) {
      return;
    }

    if (!resp.ok) {
      const detail =
        (data && (data.detail || data.message)) ||
        `HTTP ${resp.status} from backend`;
      state.assessments[state.currentQuestionIndex] = {
        questionIndex: state.currentQuestionIndex,
        transcript: "",
        normalizedTranscript: "",
        wordCount: 0,
        duration: recording.duration ?? null,
        sttOk: false,
        relevanceOk: false,
        sufficiencyOk: false,
        isValid: false,
        message: String(detail),
        relevancePercent: 0,
        relevanceThreshold: 70,
        relevanceMethod: "relevance_error",
        relevanceReason: String(detail),
        minOverallRequired: 8,
        minOverallOk: false,
        finalOverall: 0,
        step5: null,
      };
    } else {
      state.assessments[state.currentQuestionIndex] = data;
    }
  } catch (e) {
    console.error("Backend assess failed:", e);
    clearAssessTimeout();
    if (conversationState.currentQuestionIndex !== processingQuestionIndex) {
      return;
    }
    let errorMsg = "Backend error";
    if (e?.name === "AbortError") {
      errorMsg = "Backend processing timeout (Whisper took too long). Try again.";
    } else if (e?.message?.includes("Failed to fetch") || e?.message?.includes("NetworkError") || e?.code === "ECONNREFUSED") {
      errorMsg = `Backend not reachable at ${API_BASE_URL}. Start the server: cd backend && python -m uvicorn main:app --reload --port 8001`;
    } else {
      errorMsg = `Backend error: ${e?.message || String(e)}`;
    }
    state.assessments[state.currentQuestionIndex] = {
      questionIndex: state.currentQuestionIndex,
      transcript: "",
      normalizedTranscript: "",
      wordCount: 0,
      duration: recording.duration ?? null,
      sttOk: false,
      relevanceOk: false,
      sufficiencyOk: false,
      isValid: false,
      message: errorMsg,
      step5: null,
    };
  }

  updateUI();
  onProcessingDone({ success: true, reason: "ASSESSED" });
}

function startSession() {
  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  conversationState.currentQuestionIndex = 0;
  conversationState.questionTimeLeftSec = 0;
  conversationState.isMicOn = false;
  conversationState.recordings = [];
  conversationState.assessments = [];
  conversationState.repeatUsed = {};
  conversationState.levelStatus = {
    1: "available",
    2: "locked",
    3: "locked",
  };

  startGlobalTimer();
  playAvatarQuestionAudio();
  updateUI();
}

function playAvatarQuestionAudio() {
  console.log("🎬 Transitioning to next question...");
  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  updateUI();

  const q = conversationState.questions[conversationState.currentQuestionIndex];
  console.log(`🎯 Playing audio for Question ${conversationState.currentQuestionIndex + 1}:`, q.text);

  // Safety fallback: if audio fails to play or end, move to speaking state anyway after 12s
  const safetyTimeout = setTimeout(() => {
    if (conversationState.currentState === SessionState.AVATAR_SPEAKING) {
      console.log("⏰ TTS safety timeout reached - moving to USER_SPEAKING");
      onAvatarAudioEnded();
    }
  }, 12000);

  if (!ttsUnlocked) {
    if (elements.resultText) {
      elements.resultText.textContent = "⚠️ Click 'Play Question' button to hear the question.";
      elements.resultText.style.color = "inherit";
    }
  } else {
    if (elements.resultText) {
      elements.resultText.textContent = "Record your answer to see the result.";
      elements.resultText.style.color = "inherit";
    }
  }

  // Clear previous result container styles
  const resContainer = document.querySelector('.result-container');
  if (resContainer) {
    resContainer.style.background = "#fafafa";
    resContainer.style.borderColor = "rgba(0, 0, 0, 0.06)";
    resContainer.style.boxShadow = "none";
  }

  speakQuestion(q.text, { notifyOnEnd: true }).then(() => {
    clearTimeout(safetyTimeout);
  }).catch(err => {
    console.error("📢 TTS Error in flow:", err);
    clearTimeout(safetyTimeout);
    onAvatarAudioEnded();
  });
}

function onAvatarAudioEnded() {
  // Timer resume is handled in audio.onended/utter.onend callbacks
  // Only change state if we're in AVATAR_SPEAKING state
  if (conversationState.currentState === SessionState.AVATAR_SPEAKING) {
    conversationState.currentState = SessionState.USER_SPEAKING;
    conversationState.isMicOn = false;
    conversationState.questionTimeLeftSec =
      conversationState.questions[conversationState.currentQuestionIndex]
        .timeLimitSec;
    updateUI();
  }
}

async function startMic() {
  const state = conversationState;
  if (state.currentState !== SessionState.USER_SPEAKING || state.isMicOn) {
    return;
  }

  // Request mic permission when button is clicked
  const hasPermission = await ensureMicPermission();
  if (!hasPermission) {
    return;
  }

  const q = state.questions[state.currentQuestionIndex];
  conversationState.isMicOn = true;
  // Start recording only during USER_SPEAKING
  startRecordingForCurrentQuestion();
  // Live transcript (UI only)
  startLiveTranscript();
  startQuestionTimer(q.timeLimitSec);
  updateUI();
}

function stopMic() {
  const state = conversationState;
  if (!state.isMicOn) {
    return;
  }

  // Transition to processing IMMEDIATELY before stop triggers onstop
  proceedToProcessing("USER_STOPPED");

  conversationState.isMicOn = false;
  stopLiveTranscript();
  stopRecordingForCurrentQuestion();
}

function onUserTimeExpired() {
  if (conversationState.currentState !== SessionState.USER_SPEAKING) return;
  conversationState.isMicOn = false;
  stopLiveTranscript();
  stopRecordingForCurrentQuestion();
  proceedToProcessing("TIME_EXPIRED");
}

function proceedToProcessing(reason) {
  clearTimers();
  clearAssessTimeout();

  conversationState.currentState = SessionState.PROCESSING;
  updateUI();
}

function onProcessingDone(result) {
  const state = conversationState;
  const currentIdx = state.currentQuestionIndex;
  const currentLevelNum = currentIdx + 1;

  console.log(`✅ Level ${currentLevelNum} processing done. Index: ${currentIdx}`);

  // Mark current level as completed if it wasn't explicitly ignored/skipped
  if (state.levelStatus[currentLevelNum] !== "skipped") {
    state.levelStatus[currentLevelNum] = "completed";
  }

  // Update result text on the main page so they see the assessment result
  const assessment = state.assessments[currentIdx];
  if (elements.resultText && assessment) {
    const resContainer = document.querySelector('.result-container');
    if (assessment.isValid) {
      elements.resultText.innerHTML = `<span style="font-size:1.1em; display:block; margin-bottom:6px;"><strong>✅ Correct! Well done.</strong></span>${assessment.message}`;
      elements.resultText.style.color = "#155724";
      if (resContainer) {
        resContainer.style.background = "#d4edda";
        resContainer.style.borderColor = "#c3e6cb";
        resContainer.style.boxShadow = "0 4px 12px rgba(40,167,69,0.15)";
      }
    } else {
      elements.resultText.innerHTML = `<span style="font-size:1.1em; display:block; margin-bottom:6px;"><strong>⚠️ Need Improvement</strong></span>${assessment.message}`;
      elements.resultText.style.color = "#721c24";
      if (resContainer) {
        resContainer.style.background = "#f8d7da";
        resContainer.style.borderColor = "#f5c6cb";
        resContainer.style.boxShadow = "0 4px 12px rgba(220,53,69,0.15)";
      }
    }
  }

  // Check if all levels are completed or skipped
  const statuses = Object.values(state.levelStatus);
  const allLevelsDone = statuses.every(s => s === "completed" || s === "skipped");
  const isLastQuestion = currentIdx >= state.questions.length - 1;

  console.log(`📊 Stats: allLevelsDone=${allLevelsDone}, isLastQuestion=${isLastQuestion}, currentIdx=${currentIdx}`);

  if (allLevelsDone || isLastQuestion) {
    console.log("🎉 Test finished. Showing final results page.");

    // Enter waiting state before results so they can read the final "Correct" message
    conversationState.currentState = SessionState.WAITING_NEXT;
    updateUI();
    if (elements.nextLevelBtn) {
      elements.nextLevelBtn.textContent = "View Final Results";
    }
    return;
  }

  // Wait for user to click Next
  conversationState.currentState = SessionState.WAITING_NEXT;

  // Save results for AI Teacher Agent (incrementally)
  saveSpeakingResultsForAI();

  // Trigger AI Teacher Insight for this level
  const aiSection = document.getElementById('ai-teacher-section');
  if (aiSection) {
    aiSection.style.display = 'block';
    generateTeacherAnalysis('ai-report-container');
  }

  updateUI();
}

function showResultsPage() {
  showView("results");
  const state = conversationState;

  // Calculate marks for each level (0-10 each, total 30)
  let totalMarks = 0;
  const levelMarks = {
    1: 0,
    2: 0,
    3: 0
  };
  const questionResults = [];

  for (let i = 0; i < state.questions.length; i++) {
    const r = state.assessments[i];
    const levelNum = i + 1;
    const levelStatus = state.levelStatus[levelNum];

    // Handle skipped levels - marks = 0
    if (levelStatus === "skipped" || (r && r.skipped)) {
      levelMarks[levelNum] = 0;
      questionResults.push({
        level: levelNum,
        status: "SKIPPED",
        marks: 0,
        overall: 0,
        overallPercent: 0,
        message: "Level skipped",
        step5: null
      });
      continue;
    }

    // Handle no result - marks = 0
    if (!r || !r.step5) {
      levelMarks[levelNum] = 0;
      questionResults.push({
        level: levelNum,
        status: "FAIL",
        marks: 0,
        overall: 0,
        overallPercent: 0,
        message: r?.message || "Backend not called / failed",
        step5: null
      });
      continue;
    }

    // Calculate marks based on overall score (0-10 scale)
    // The step5.overall is already on 0-10 scale, so use it directly as marks
    const overallScore = r.step5.overall || 0;
    const marks = Math.max(0, Math.min(10, overallScore)); // Clamp between 0-10
    levelMarks[levelNum] = marks;
    totalMarks += marks;

    const overallPercent = r.step5.overallPercent || 0;
    const isValid = r.isValid || false;

    questionResults.push({
      level: levelNum,
      status: isValid ? "PASS" : "FAIL",
      marks: marks,
      overall: overallScore,
      overallPercent: overallPercent,
      message: r.message || "",
      step5: r.step5
    });
  }

  // Calculate percentage (total marks out of 30)
  const totalPercentage = (totalMarks / 30) * 100;

  // Calculate overall aggregate scores (average across all 3 levels)
  let totalFluency = 0, totalPronunciation = 0, totalConfidence = 0, totalCoherence = 0, totalLexical = 0;
  let validLevelsCount = 0;

  questionResults.forEach(qr => {
    if (qr.step5 && qr.status !== "SKIPPED") {
      totalFluency += qr.step5.fluency || 0;
      totalPronunciation += qr.step5.pronunciation || 0;
      totalConfidence += qr.step5.confidence || 0;
      totalCoherence += qr.step5.coherence || 0;
      totalLexical += qr.step5.lexical || 0;
      validLevelsCount++;
    }
  });

  const avgFluency = validLevelsCount > 0 ? totalFluency / validLevelsCount : 0;
  const avgPronunciation = validLevelsCount > 0 ? totalPronunciation / validLevelsCount : 0;
  const avgConfidence = validLevelsCount > 0 ? totalConfidence / validLevelsCount : 0;
  const avgCoherence = validLevelsCount > 0 ? totalCoherence / validLevelsCount : 0;
  const avgLexical = validLevelsCount > 0 ? totalLexical / validLevelsCount : 0;

  // Convert to percentages
  const avgFluencyPercent = (avgFluency / 10) * 100;
  const avgPronunciationPercent = (avgPronunciation / 10) * 100;
  const avgConfidencePercent = (avgConfidence / 10) * 100;
  const avgCoherencePercent = (avgCoherence / 10) * 100;
  const avgLexicalPercent = (avgLexical / 10) * 100;

  // Update results display
  if (elements.resultStatusText) {
    const allPassed = questionResults.every(qr => qr.status === "PASS");
    elements.resultStatusText.textContent = allPassed ? "PASSED" : "COMPLETED";
  }

  if (elements.resultMarksText) {
    elements.resultMarksText.textContent = `${totalMarks.toFixed(2)} / 30`;
  }

  if (elements.resultPercentage) {
    elements.resultPercentage.textContent = `Percentage: ${totalPercentage.toFixed(2)}%`;
  }

  // Show detailed results
  if (elements.detailedResults) {
    let html = "";

    // Overall Summary Section
    html += `<div style="margin-bottom: 30px; padding: 20px; background: #f8f9fa; border-radius: 12px; border: 1px solid rgba(0, 0, 0, 0.08);">`;
    html += `<h3 style="margin-top: 0; margin-bottom: 20px; color: #000; font-size: 1.3em; font-weight: 700;">Overall Summary</h3>`;
    html += `<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 15px;">`;
    html += `<div><strong>Total Marks:</strong> <span style="font-size: 1.2em; font-weight: 700; color: #000;">${totalMarks.toFixed(2)} / 30</span></div>`;
    html += `<div><strong>Percentage:</strong> <span style="font-size: 1.2em; font-weight: 700; color: #000;">${totalPercentage.toFixed(2)}%</span></div>`;
    html += `</div>`;
    html += `</div>`;

    // Overall Aggregate Scores Section
    html += `<div style="margin-bottom: 30px; padding: 20px; background: #ffffff; border-radius: 12px; border: 1px solid rgba(0, 0, 0, 0.08);">`;
    html += `<h3 style="margin-top: 0; margin-bottom: 20px; color: #000; font-size: 1.2em; font-weight: 700;">Overall Scores (Average across all levels)</h3>`;
    html += `<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px;">`;
    html += `<div style="padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    html += `<div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Fluency</div>`;
    html += `<div style="font-size: 1.3em; font-weight: 700; color: #000;">${avgFluencyPercent.toFixed(1)}%</div>`;
    html += `<div style="font-size: 0.85em; color: #999;">(${avgFluency.toFixed(2)}/10)</div>`;
    html += `</div>`;
    html += `<div style="padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    html += `<div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Pronunciation</div>`;
    html += `<div style="font-size: 1.3em; font-weight: 700; color: #000;">${avgPronunciationPercent.toFixed(1)}%</div>`;
    html += `<div style="font-size: 0.85em; color: #999;">(${avgPronunciation.toFixed(2)}/10)</div>`;
    html += `</div>`;
    html += `<div style="padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    html += `<div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Confidence</div>`;
    html += `<div style="font-size: 1.3em; font-weight: 700; color: #000;">${avgConfidencePercent.toFixed(1)}%</div>`;
    html += `<div style="font-size: 0.85em; color: #999;">(${avgConfidence.toFixed(2)}/10)</div>`;
    html += `</div>`;
    html += `<div style="padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    html += `<div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Coherence</div>`;
    html += `<div style="font-size: 1.3em; font-weight: 700; color: #000;">${avgCoherencePercent.toFixed(1)}%</div>`;
    html += `<div style="font-size: 0.85em; color: #999;">(${avgCoherence.toFixed(2)}/10)</div>`;
    html += `</div>`;
    html += `<div style="padding: 12px; background: #f8f9fa; border-radius: 8px;">`;
    html += `<div style="font-size: 0.9em; color: #666; margin-bottom: 5px;">Lexical</div>`;
    html += `<div style="font-size: 1.3em; font-weight: 700; color: #000;">${avgLexicalPercent.toFixed(1)}%</div>`;
    html += `<div style="font-size: 0.85em; color: #999;">(${avgLexical.toFixed(2)}/10)</div>`;
    html += `</div>`;
    html += `</div>`;
    html += `</div>`;

    // Level-wise Results Section
    html += `<div style="margin-bottom: 20px;">`;
    html += `<h3 style="margin-bottom: 20px; color: #000; font-size: 1.2em; font-weight: 700;">Level-wise Marks</h3>`;

    // Show individual level marks
    questionResults.forEach(qr => {
      html += `<div class="result-item" style="margin-bottom: 15px; padding: 15px; background: #ffffff; border-radius: 8px; border: 1px solid rgba(0, 0, 0, 0.08); display: flex; justify-content: space-between; align-items: center;">`;
      html += `<div>`;
      html += `<div class="result-item-label" style="font-size: 1.1em; font-weight: 600; color: #000; margin-bottom: 8px;">Level ${qr.level}</div>`;
      if (qr.step5) {
        html += `<div style="font-size: 0.85em; color: #666;">`;
        html += `Fluency: ${qr.step5.fluencyPercent.toFixed(1)}% | `;
        html += `Pronunciation: ${qr.step5.pronunciationPercent.toFixed(1)}% | `;
        html += `Confidence: ${qr.step5.confidencePercent.toFixed(1)}% | `;
        html += `Coherence: ${qr.step5.coherencePercent.toFixed(1)}% | `;
        html += `Lexical: ${qr.step5.lexicalPercent.toFixed(1)}%`;
        html += `</div>`;
      }
      html += `</div>`;
      html += `<div style="text-align: right;">`;

      // Show marks out of 10
      if (qr.status === "SKIPPED") {
        html += `<div class="result-item-value" style="color: #ff9800; font-size: 1.5em; font-weight: 700;">0 / 10</div>`;
        html += `<div style="font-size: 0.9em; color: #ff9800; margin-top: 4px;">SKIPPED</div>`;
      } else if (qr.status === "FAIL" || qr.marks === 0) {
        html += `<div class="result-item-value" style="color: #dc3545; font-size: 1.5em; font-weight: 700;">0 / 10</div>`;
        html += `<div style="font-size: 0.9em; color: #dc3545; margin-top: 4px;">FAIL</div>`;
      } else {
        html += `<div class="result-item-value" style="font-size: 1.5em; font-weight: 700; color: #000;">${qr.marks.toFixed(2)} / 10</div>`;
        html += `<div style="font-size: 0.9em; color: #666; margin-top: 4px;">${qr.overallPercent.toFixed(1)}%</div>`;
      }
      html += `</div>`;
      html += `</div>`;
    });

    html += `</div>`;

    elements.detailedResults.innerHTML = html;
  }

  // Show "Continue with Reading Assessment" for intermediate and advanced (both have reading after speaking)
  var actionsEl = document.getElementById("results-actions");
  var showReadingBtn = flowLevel === "intermediate" || flowLevel === "advanced";
  if (actionsEl && showReadingBtn) {
    var existing = document.getElementById("continue-reading-btn");
    if (!existing) {
      var a = document.createElement("a");
      a.id = "continue-reading-btn";
      a.href = "continue-reading.html?level=" + encodeURIComponent(flowLevel);
      a.className = "btn-primary dashboard-btn";
      a.style.cssText = "display: inline-block; text-decoration: none; text-align: center;";
      a.textContent = "Continue with Reading Assessment";
      actionsEl.insertBefore(a, actionsEl.firstChild);
    }
  } else if (actionsEl) {
    var toRemove = document.getElementById("continue-reading-btn");
    if (toRemove) toRemove.remove();
  }

  // Save final results for Teacher Agent
  saveSpeakingResultsForAI(questionResults);

  // Show AI Teacher Section
  const aiSection = document.getElementById('final-ai-teacher-section');
  if (aiSection) {
    aiSection.style.display = 'block';
    generateTeacherAnalysis('final-ai-report-container');
  }

  // Notify Assessment Flow system
  if (typeof window.assessmentFlowComplete === 'function') {
    window.assessmentFlowComplete(questionResults);
  }
}

function restartTest() {
  // Reset state
  conversationState.currentState = SessionState.INIT;
  conversationState.currentQuestionIndex = 0;
  conversationState.questionTimeLeftSec = 0;
  conversationState.globalTimeLeftSec = 10 * 60;
  conversationState.isMicOn = false;
  conversationState.recordings = [];
  conversationState.assessments = [];
  conversationState.repeatUsed = {};
  conversationState.levelStatus = {
    1: "locked",
    2: "locked",
    3: "locked",
  };

  // Clear timers
  clearTimers();
  clearAssessTimeout();

  // Stop any ongoing recording
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try {
      mediaRecorder.stop();
    } catch (e) { }
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  stopLiveTranscript();

  // Reset UI
  if (elements.globalTimer) {
    elements.globalTimer.textContent = "10:00";
    elements.globalTimer.classList.remove("warning", "expired");
  }

  // Show test page and restart
  showView("test");
  startSession();
  updateUI();
}

// Make restartTest available globally
window.restartTest = restartTest;

function goToNextQuestion() {
  const state = conversationState;
  const currentIdx = state.currentQuestionIndex;
  const nextIndex = currentIdx + 1;

  console.log(`⏭️ Manual Next Question triggered. current: ${currentIdx}, next: ${nextIndex}`);

  if (nextIndex >= state.questions.length) {
    console.log("🏁 No more questions, finishing.");
    conversationState.currentState = SessionState.END;
    clearTimers();
    clearAssessTimeout();
    updateUI();
    showResultsPage();
    return;
  }

  // Mark current as completed if we're jumping from it
  state.levelStatus[currentIdx + 1] = "completed";

  conversationState.currentQuestionIndex = nextIndex;
  const nextLevelNum = nextIndex + 1;
  state.levelStatus[nextLevelNum] = "available";

  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  conversationState.isMicOn = false;
  conversationState.repeatUsed[nextIndex] = 0;

  updateUI();
  playAvatarQuestionAudio();
}

function skipCurrentLevel() {
  const state = conversationState;
  const currentLevel = state.currentQuestionIndex + 1;

  // Mark current level as skipped
  state.levelStatus[currentLevel] = "skipped";

  // Mark current question as skipped (score 0)
  state.assessments[state.currentQuestionIndex] = {
    questionIndex: state.currentQuestionIndex,
    transcript: "",
    normalizedTranscript: "",
    wordCount: 0,
    duration: 0,
    sttOk: false,
    relevanceOk: false,
    sufficiencyOk: false,
    isValid: false,
    message: "Level skipped by user",
    relevancePercent: 0,
    overallPercent: 0,
    step5: null,
    skipped: true,
  };

  // Check if all levels are done
  const allLevelsDone = Object.values(state.levelStatus).every(
    status => status === "completed" || status === "skipped"
  );

  if (allLevelsDone) {
    conversationState.currentState = SessionState.END;
    clearTimers();
    clearAssessTimeout();
    updateUI();
    showResultsPage();
    return;
  }

  // Auto-advance to next question after skipping
  const nextIndex = state.currentQuestionIndex + 1;
  if (nextIndex < state.questions.length) {
    // Unlock next level if it was locked
    const nextLevel = nextIndex + 1;
    if (nextLevel <= 3 && state.levelStatus[nextLevel] === "locked") {
      state.levelStatus[nextLevel] = "available";
    }

    conversationState.currentQuestionIndex = nextIndex;
    conversationState.currentState = SessionState.AVATAR_SPEAKING;
    conversationState.isMicOn = false;
    conversationState.repeatUsed[nextIndex] = 0; // Reset repeat count for new question
    updateUI();
    playAvatarQuestionAudio();
  } else {
    // No more questions - should have been caught by allLevelsDone check above
    conversationState.currentState = SessionState.USER_SPEAKING;
    conversationState.isMicOn = false;
    updateUI();
  }
}

// Function to unlock TTS
function unlockTTS() {
  if (!ttsUnlocked && window.speechSynthesis) {
    console.log("🔓 Unlocking TTS...");
    // Try to speak a silent utterance to unlock TTS
    try {
      const testUtterance = new SpeechSynthesisUtterance("");
      testUtterance.volume = 0;
      testUtterance.onstart = () => {
        window.speechSynthesis.cancel();
        ttsUnlocked = true;
        console.log("✅ TTS unlocked!");
        // After unlocking, try to play the current question if in AVATAR_SPEAKING state
        if (conversationState.currentState === SessionState.AVATAR_SPEAKING) {
          const q = conversationState.questions[conversationState.currentQuestionIndex];
          if (q) {
            // Already handled by playAvatarQuestionAudio, don't double trigger
            console.log("TTS unlocked, checking if audio is already playing");
          }
        }
      };
      window.speechSynthesis.speak(testUtterance);
      setTimeout(() => {
        window.speechSynthesis.cancel();
        if (!ttsUnlocked) {
          ttsUnlocked = true;
          console.log("✅ TTS unlocked (fallback)!");
          // After unlocking, try to play the current question if in AVATAR_SPEAKING state
          if (conversationState.currentState === SessionState.AVATAR_SPEAKING) {
            const q = conversationState.questions[conversationState.currentQuestionIndex];
            if (q) {
              // Already handled, don't double trigger
            }
          }
        }
      }, 100);
    } catch (e) {
      console.error("Failed to unlock TTS:", e);
      ttsUnlocked = true; // Assume unlocked anyway
    }
  }
}

// Combined Play/Repeat Question button handler
function playRepeatQuestion() {
  unlockTTS();
  const state = conversationState;
  const q = state.questions[state.currentQuestionIndex];

  if (!q) return;

  // Check if this is a repeat (user has already heard the question)
  const repeatCount = state.repeatUsed[state.currentQuestionIndex] || 0;
  const maxRepeats = 2;

  // If it's a repeat and user hasn't started mic yet
  if (repeatCount > 0 && state.currentState === SessionState.USER_SPEAKING && !state.isMicOn) {
    if (repeatCount >= maxRepeats) {
      return; // Max repeats reached
    }
    // Increment repeat count
    conversationState.repeatUsed[state.currentQuestionIndex] = repeatCount + 1;
  } else if (repeatCount === 0) {
    // First time playing - mark as played
    conversationState.repeatUsed[state.currentQuestionIndex] = 1;
  }

  // Play the question
  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  // Don't pause timer here - only pause when audio actually starts
  updateUI();
  speakQuestion(q.text, { notifyOnEnd: true });
}

// Combined Mic Toggle button handler
function toggleMic() {
  const state = conversationState;

  if (state.isMicOn) {
    // Currently recording - process result and move to next question
    stopMic();
    // After processing is done, it will automatically move to next question
    // The onProcessingDone function handles this
  } else {
    // Not recording - start it
    startMic();
  }
}

// Skip level handler
function skipCurrentLevel() {
  const state = conversationState;
  const currentIdx = state.currentQuestionIndex;

  if (currentIdx >= state.questions.length || state.currentState === SessionState.END) {
    return;
  }

  // Stop pending processes
  if (state.isMicOn) stopMic();
  clearTimers();
  clearAssessTimeout();

  // Mark skipped natively without backend hit
  const currentLevelNum = currentIdx + 1;
  state.levelStatus[currentLevelNum] = "skipped";
  state.assessments[currentIdx] = {
    isValid: false,
    skipped: true,
    message: "Level entirely skipped by user.",
    step5: null
  };

  // Skip visual transition wrapper
  onProcessingDone({ success: true, reason: "SKIPPED" });
}

// Next Question Handler (handles explicit next and end state)
function goToNextQuestion() {
  const state = conversationState;
  const currentIdx = state.currentQuestionIndex;

  // Handle case where STT/TTS gets stuck
  if (state.currentState === SessionState.PROCESSING) {
    skipCurrentLevel();
    return;
  }

  if (state.currentState === SessionState.WAITING_NEXT) {
    const isLastQuestion = currentIdx >= state.questions.length - 1;
    const statuses = Object.values(state.levelStatus);
    const allLevelsDone = statuses.every(s => s === "completed" || s === "skipped");

    if (isLastQuestion || allLevelsDone) {
      state.currentState = SessionState.END;
      clearTimers();
      clearAssessTimeout();
      showResultsPage();
      updateUI();
    } else {
      const nextIndex = currentIdx + 1;
      const nextLevelNum = nextIndex + 1;

      console.log(`➡️ Advancing to Level ${nextLevelNum}. Index: ${nextIndex}`);
      state.levelStatus[nextLevelNum] = "available";
      state.currentQuestionIndex = nextIndex;
      state.currentState = SessionState.AVATAR_SPEAKING;
      state.isMicOn = false;
      state.repeatUsed[nextIndex] = 0;

      updateUI();
      // Hide AI Teacher report when moving to next level
      const aiSection = document.getElementById('ai-teacher-section');
      if (aiSection) aiSection.style.display = 'none';
      playAvatarQuestionAudio();
    }
  }
}

// Wait for DOM to be ready before initializing
document.addEventListener("DOMContentLoaded", () => {
  // Set up event listeners
  if (elements.playRepeatQuestionBtn) elements.playRepeatQuestionBtn.addEventListener("click", playRepeatQuestion);
  if (elements.micToggleBtn) elements.micToggleBtn.addEventListener("click", toggleMic);
  if (elements.skipLevelBtn) elements.skipLevelBtn.addEventListener("click", skipCurrentLevel);
  if (elements.nextLevelBtn) elements.nextLevelBtn.addEventListener("click", goToNextQuestion);

  // Unlock TTS on any user interaction and auto-play question
  function handleFirstInteraction() {
    unlockTTS();
    // Remove listeners after first interaction
    document.removeEventListener("click", handleFirstInteraction);
    document.removeEventListener("keydown", handleFirstInteraction);
    document.removeEventListener("touchstart", handleFirstInteraction);
  }

  document.addEventListener("click", handleFirstInteraction, { once: true });
  document.addEventListener("keydown", handleFirstInteraction, { once: true });
  document.addEventListener("touchstart", handleFirstInteraction, { once: true });

  // Load Tamil voices
  loadVoices();

  // Start session automatically on page load (no rules page)
  if (conversationState.currentState === SessionState.INIT) {
    prewarmSpeechRecognitionPermission();
    // Small delay to ensure DOM is fully ready
    setTimeout(() => {
      startSession();
    }, 100);
  }
});


// Level button navigation - only allow navigation to unlocked levels
if (elements.level1Btn) {
  elements.level1Btn.addEventListener("click", () => {
    const state = conversationState;
    if (state.levelStatus[1] !== "locked" && state.currentQuestionIndex !== 0) {
      state.currentQuestionIndex = 0;
      state.currentState = SessionState.AVATAR_SPEAKING;
      state.isMicOn = false;
      clearTimers();
      playAvatarQuestionAudio();
      updateUI();
    }
  });
}

if (elements.level2Btn) {
  elements.level2Btn.addEventListener("click", () => {
    const state = conversationState;
    if (state.levelStatus[2] !== "locked" && state.currentQuestionIndex !== 1) {
      state.currentQuestionIndex = 1;
      state.currentState = SessionState.AVATAR_SPEAKING;
      state.isMicOn = false;
      clearTimers();
      playAvatarQuestionAudio();
      updateUI();
    }
  });
}

if (elements.level3Btn) {
  elements.level3Btn.addEventListener("click", () => {
    const state = conversationState;
    if (state.levelStatus[3] !== "locked" && state.currentQuestionIndex !== 2) {
      state.currentQuestionIndex = 2;
      state.currentState = SessionState.AVATAR_SPEAKING;
      state.isMicOn = false;
      clearTimers();
      playAvatarQuestionAudio();
      updateUI();
    }
  });
}

// Initialize - start test directly
updateUI();


// Helper to save speaking results to localStorage for TeacherAgent
function saveSpeakingResultsForAI(providedResults = null) {
  const state = conversationState;
  let resultsToSave = providedResults;

  if (!resultsToSave) {
    // Generate on-the-fly if not provided (for per-level view)
    resultsToSave = state.questions.map((q, i) => {
      const r = state.assessments[i];
      const levelNum = i + 1;
      const status = state.levelStatus[levelNum];

      if (status === "skipped" || (r && r.skipped)) {
        return { level: levelNum, status: "SKIPPED", marks: 0 };
      }
      if (!r || !r.step5) {
        return { level: levelNum, status: status === "completed" ? "PENDING" : status.toUpperCase(), marks: 0 };
      }

      return {
        level: levelNum,
        status: r.isValid ? "PASS" : "FAIL",
        marks: r.step5.overall || 0,
        question_text: q.text,
        transcript: r.transcript || r.normalizedTranscript || "",
        relevance_reason: r.relevanceReason || "",
        step5: r.step5,
        message: r.message
      };
    });
  }

  localStorage.setItem('speakingResults', JSON.stringify(resultsToSave));
}

// AI Teacher Report Generator (Shared Logic)
async function generateTeacherAnalysis(containerId) {
  const container = document.getElementById(containerId);
  if (container && window.teacherAgent) {
    // Show loading state
    container.innerHTML = `
      <div class="loading-ai">
        <div class="spinner-ai"></div>
        <p>Your AI Teacher is analyzing your speech performance...</p>
      </div>
    `;

    try {
      const reportMarkdown = await window.teacherAgent.generateReport();
      const renderedHTML = typeof marked !== 'undefined' ? marked.parse(reportMarkdown) : reportMarkdown.replace(/\n/g, '<br>');

      container.innerHTML = `
        <div class="ai-report-card">
          <div class="ai-report-content">
            ${renderedHTML}
          </div>
          <div class="ai-report-actions">
            <button onclick="window.teacherAgent.downloadPDF(\`${reportMarkdown.replace(/`/g, '\\`').replace(/\$/g, '\\$')}\`)" 
                    class="pdf-btn">
              <svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              Download PDF Report
            </button>
          </div>
        </div>
      `;
    } catch (error) {
      console.error('Teacher Analysis Error:', error);
      container.innerHTML = `
        <div class="ai-report-card" style="border-left-color: #dc3545;">
          <p style="color: #dc3545; font-weight: 600;">Teacher Service Unavailable</p>
          <p style="font-size: 0.9em; margin-top: 10px;">${error.message}</p>
        </div>
      `;
    }
  }
}
