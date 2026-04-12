// MODULE 1: Conversation Orchestrator (HTML + JS implementation)

const SessionState = {
  INIT: "INIT",
  AVATAR_SPEAKING: "AVATAR_SPEAKING",
  USER_SPEAKING: "USER_SPEAKING",
  PROCESSING: "PROCESSING",
  SHOWING_RESULT: "SHOWING_RESULT", // New state to show result before moving to next question
  END: "END",
};

// Backend (FastAPI) base URL for STEP 4/5
const API_BASE_URL = "http://127.0.0.1:8000";

// Central single source of truth for the conversation
const conversationState = {
  currentState: SessionState.INIT,
  currentQuestionIndex: 0,
  questions: [
    {
      id: 1,
      level: "basic",
      text: "नई चीजें सीखना क्यों जरूरी है, आप क्या सोचते हैं?",
      timeLimitSec: 75,
    },
    {
      id: 2,
      level: "mid",
      text: "अगर आप किसी नई जगह जाएं तो वहाँ के लोगों के साथ कैसे घुलमिल जाएंगे?",
      timeLimitSec: 90,
    },
    {
      id: 3,
      level: "final",
      text: "समय प्रबंधन जीवन में कितना महत्वपूर्ण है, इसे उदाहरण के साथ बताइए।",
      timeLimitSec: 120,
    },
  ],
  recordings: [],
  assessments: [], // per questionIndex: response from /api/assess-answer
  timers: {
    question: null,
  },
  questionTimeLeftSec: 0,
  isMicOn: false,
  repeatUsed: {}, // questionIndex -> boolean (only one repeat allowed)
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

const elements = {
  rulesPage: document.getElementById("rules-page"),
  testPage: document.getElementById("test-page"),
  resultsPage: document.getElementById("results-page"),
  beginTestBtn: document.getElementById("begin-test-btn"),
  stateLabel: document.getElementById("state-label"),
  questionIndex: document.getElementById("question-index"),
  questionTimer: document.getElementById("question-timer"),
  questionText: document.getElementById("question-text"),
  liveTranscript: document.getElementById("live-transcript"),
  resultText: document.getElementById("result-text"),
  repeatQuestionBtn: document.getElementById("repeat-question-btn"),
  startMicBtn: document.getElementById("start-mic-btn"),
  stopMicBtn: document.getElementById("stop-mic-btn"),
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
  nextQuestionBtn: document.getElementById("next-question-btn"),
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
  elements.rulesPage?.classList.add("hidden");
  elements.testPage?.classList.add("hidden");
  elements.resultsPage?.classList.add("hidden");
  
  // Show requested page
  if (view === "rules") {
    elements.rulesPage?.classList.remove("hidden");
  } else if (view === "test") {
    elements.testPage?.classList.remove("hidden");
  } else if (view === "results") {
    elements.resultsPage?.classList.remove("hidden");
  }
}

function updateUI() {
  const state = conversationState;

  if (elements.stateLabel) elements.stateLabel.textContent = state.currentState;

  if (state.currentQuestionIndex < 0) {
    if (elements.questionIndex) elements.questionIndex.textContent = "-";
    if (elements.questionText) elements.questionText.textContent = 'Test will start after you click "Start Test".';
    if (elements.questionProgress) elements.questionProgress.textContent = "";
  } else if (state.currentQuestionIndex < state.questions.length) {
    const q = state.questions[state.currentQuestionIndex];
    if (elements.questionIndex) {
      elements.questionIndex.textContent = `${state.currentQuestionIndex + 1} / ${state.questions.length}`;
    }
    if (elements.questionText) elements.questionText.textContent = q.text;
    if (elements.questionProgress) {
      elements.questionProgress.textContent = `Question ${state.currentQuestionIndex + 1} of ${state.questions.length} (${q.level})`;
    }
    if (elements.testSubtitle) {
      elements.testSubtitle.textContent = `Question ${state.currentQuestionIndex + 1} - ${q.level.toUpperCase()}`;
    }
  } else {
    if (elements.questionIndex) elements.questionIndex.textContent = "Completed";
    if (elements.questionProgress) elements.questionProgress.textContent = "All questions completed";
  }

  if (elements.questionTimer) elements.questionTimer.textContent = formatTime(state.questionTimeLeftSec);

  // Live transcript UI
  if (elements.liveTranscript) {
    if (state.currentState === SessionState.SHOWING_RESULT) {
      // Keep transcript visible when showing results - don't change it here
      // It's already set in the SHOWING_RESULT section above
    } else if (state.currentState === SessionState.USER_SPEAKING) {
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
    } else if (state.currentState === SessionState.PROCESSING) {
      // keep last transcript visible
    } else {
      elements.liveTranscript.textContent =
        "Press \"Start Mic\" and speak to see live captions…";
    }
  }

  // Result box
  if (state.currentState === SessionState.PROCESSING) {
    if (elements.resultText) elements.resultText.textContent = "Processing… Please wait.";
    if (elements.nextQuestionBtn) {
      elements.nextQuestionBtn.style.display = "none";
      elements.nextQuestionBtn.disabled = true;
    }
  } else if (state.currentState === SessionState.SHOWING_RESULT) {
    // Show result for current question
    const res = state.assessments[state.currentQuestionIndex];
    if (res) {
      // Show transcript from backend response
      const transcript = res.transcript || res.normalizedTranscript || "";
      if (elements.liveTranscript && transcript) {
        elements.liveTranscript.textContent = transcript;
        elements.liveTranscript.style.fontWeight = "normal";
        elements.liveTranscript.style.color = "#333";
      }
      
      let resultMsg = "";
      const relStatus = res.relevanceStatus || (typeof res.relevancePercent === "number"
        ? (res.relevancePercent >= 10 ? "Relevant" : "Not Relevant")
        : "n/a");

      if (res.step5) {
        // Answer passed - show all factor percentages
        resultMsg = `✅ Answer is Relevant!\n\n`;
        resultMsg += `📝 Your Answer:\n${transcript}\n\n`;
        resultMsg += `📊 Speaking Skills Breakdown:\n\n`;
        resultMsg += `• Fluency: ${res.step5.fluencyPercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Pronunciation: ${res.step5.pronunciationPercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Confidence: ${res.step5.confidencePercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Coherence: ${res.step5.coherencePercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Lexical: ${res.step5.lexicalPercent?.toFixed(1) || 0}%\n\n`;
        resultMsg += `━━━━━━━━━━━━━━━━━━━━\n`;
        resultMsg += `Overall Score: ${res.step5.overallPercent?.toFixed(1) || 0}%`;
      } else {
        // Answer failed relevance check
        resultMsg = `❌ FAIL\n\n`;
        resultMsg += `📝 Your Answer:\n${transcript}\n\n`;
        resultMsg += `Answer context does not match the question.\n`;
        resultMsg += `Relevance: ${res.relevancePercent?.toFixed(1) || 0}% (Required: 10%)`;
      }
      if (elements.resultText) elements.resultText.textContent = resultMsg;
    }
    
    // Show Next Question button if not last question
    const isLastQuestion = state.currentQuestionIndex >= state.questions.length - 1;
    if (elements.nextQuestionBtn) {
      if (isLastQuestion) {
        elements.nextQuestionBtn.style.display = "none";
      } else {
        elements.nextQuestionBtn.style.display = "inline-block";
        elements.nextQuestionBtn.disabled = false;
        elements.nextQuestionBtn.textContent = "Next Question";
      }
    }
    
    // Hide other buttons during result display
    if (elements.startMicBtn) elements.startMicBtn.style.display = "none";
    if (elements.stopMicBtn) elements.stopMicBtn.style.display = "none";
    if (elements.repeatQuestionBtn) elements.repeatQuestionBtn.style.display = "none";
  } else if (state.currentState === SessionState.END) {
    // Show results page
    showResultsPage();
  } else if (
    typeof state.currentQuestionIndex === "number" &&
    state.currentQuestionIndex >= 0
  ) {
    const res = state.assessments[state.currentQuestionIndex];
    if (!res) {
      if (elements.resultText) elements.resultText.textContent = "Record your answer to see the result.";
    } else {
      // Show detailed result for current question
      let resultMsg = "";
      const relStatus = res.relevanceStatus || (typeof res.relevancePercent === "number"
        ? (res.relevancePercent >= 10 ? "Relevant" : "Not Relevant")
        : "n/a");

      // Show transcript from backend response
      const transcript = res.transcript || res.normalizedTranscript || "";
      if (elements.liveTranscript && transcript) {
        elements.liveTranscript.textContent = transcript;
        elements.liveTranscript.style.fontWeight = "normal";
        elements.liveTranscript.style.color = "#333";
      }
      
      if (res.step5) {
        // Answer passed - show all factor percentages
        resultMsg = `✅ Answer is Relevant!\n\n`;
        resultMsg += `📝 Your Answer:\n${transcript}\n\n`;
        resultMsg += `📊 Speaking Skills Breakdown:\n\n`;
        resultMsg += `• Fluency: ${res.step5.fluencyPercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Pronunciation: ${res.step5.pronunciationPercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Confidence: ${res.step5.confidencePercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Coherence: ${res.step5.coherencePercent?.toFixed(1) || 0}%\n`;
        resultMsg += `• Lexical: ${res.step5.lexicalPercent?.toFixed(1) || 0}%\n\n`;
        resultMsg += `━━━━━━━━━━━━━━━━━━━━\n`;
        resultMsg += `Overall Score: ${res.step5.overallPercent?.toFixed(1) || 0}%`;
      } else {
        // Answer failed relevance check
        resultMsg = `❌ FAIL\n\n`;
        resultMsg += `📝 Your Answer:\n${transcript}\n\n`;
        resultMsg += `Answer context does not match the question.\n`;
        resultMsg += `Relevance: ${res.relevancePercent?.toFixed(1) || 0}% (Required: 10%)`;
      }
      if (elements.resultText) elements.resultText.textContent = resultMsg;
    }
    
    // Hide Next Question button during normal flow
    if (elements.nextQuestionBtn) {
      elements.nextQuestionBtn.style.display = "none";
      elements.nextQuestionBtn.disabled = true;
    }
    
    // Show normal buttons
    if (elements.startMicBtn) elements.startMicBtn.style.display = "inline-block";
    if (elements.stopMicBtn) elements.stopMicBtn.style.display = "inline-block";
    if (elements.repeatQuestionBtn) elements.repeatQuestionBtn.style.display = "inline-block";
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

  const canUseMicPhase = state.currentState === SessionState.USER_SPEAKING;
  if (elements.startMicBtn) elements.startMicBtn.disabled = !canUseMicPhase || state.isMicOn;
  if (elements.stopMicBtn) elements.stopMicBtn.disabled = !canUseMicPhase || !state.isMicOn;

  const repeatAlreadyUsed = !!state.repeatUsed[state.currentQuestionIndex];
  // Repeat allowed until user starts mic (i.e., during USER_SPEAKING while mic is OFF)
  const canRepeat =
    state.currentState === SessionState.USER_SPEAKING &&
    !state.isMicOn &&
    state.currentQuestionIndex >= 0 &&
    state.currentQuestionIndex < state.questions.length &&
    !repeatAlreadyUsed;
  if (elements.repeatQuestionBtn) elements.repeatQuestionBtn.disabled = !canRepeat;
}

function clearTimers() {
  if (conversationState.timers.question) {
    clearInterval(conversationState.timers.question);
    conversationState.timers.question = null;
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
    } catch (_) {}
    assessAbortController = null;
  }
}

let currentUtterance = null;

// TTS engine for avatar; not aware of global FSM, only uses callback
function speakQuestion(text, { notifyOnEnd } = { notifyOnEnd: true }) {
  if (!window.speechSynthesis) {
    console.warn("speechSynthesis not supported in this browser.");
    if (notifyOnEnd) {
      setTimeout(onAvatarAudioEnded, 2000);
    }
    return;
  }

  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(text);
  utter.lang = "hi-IN"; // Hindi voice
  utter.volume = 1.0; // max volume
  utter.rate = 0.9; // slightly slower for clarity
  utter.pitch = 1.0;

  if (notifyOnEnd) {
    utter.onend = () => {
      onAvatarAudioEnded();
    };
  }

  currentUtterance = utter;
  window.speechSynthesis.speak(utter);
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
  rec.lang = "hi-IN";
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
      } catch (_) {}
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
  const minDurationSec = 5;
  const minSizeBytes = 5000;

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
    clearProcessingTimeout();
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
  // Send browser live transcript to backend so it can use the most accurate text
  if (typeof finalTranscript === "string" && finalTranscript.trim().length > 0) {
    form.append("clientTranscript", finalTranscript.trim());
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
      } catch (_) {}
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
      errorMsg = `Backend not reachable at ${API_BASE_URL}. Start the server: cd backend && python -m uvicorn main:app --reload --port 8000`;
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

  playAvatarQuestionAudio();
  updateUI();
}

function playAvatarQuestionAudio() {
  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  updateUI();

  const q = conversationState.questions[conversationState.currentQuestionIndex];
  speakQuestion(q.text, { notifyOnEnd: true });
}

function onAvatarAudioEnded() {
  if (conversationState.currentState !== SessionState.AVATAR_SPEAKING) return;

  // Avatar finished asking question; now user can choose when to start mic.
  conversationState.currentState = SessionState.USER_SPEAKING;
  conversationState.isMicOn = false;
  conversationState.questionTimeLeftSec =
    conversationState.questions[conversationState.currentQuestionIndex]
      .timeLimitSec;
  updateUI();
}

function startMic() {
  const state = conversationState;
  if (state.currentState !== SessionState.USER_SPEAKING || state.isMicOn) {
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
  // Here is where you'd start real microphone recording / STT.
}

function stopMic() {
  const state = conversationState;
  if (state.currentState !== SessionState.USER_SPEAKING || !state.isMicOn) {
    return;
  }
  conversationState.isMicOn = false;
  stopLiveTranscript();
  stopRecordingForCurrentQuestion();
  proceedToProcessing("USER_STOPPED");
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
  const isLastQuestion =
    state.currentQuestionIndex >= state.questions.length - 1;
  if (isLastQuestion) {
    conversationState.currentState = SessionState.END;
    clearTimers();
    clearAssessTimeout();
    updateUI();
    return;
  }

  // Show result first, wait for user to click "Next Question"
  conversationState.currentState = SessionState.SHOWING_RESULT;
  clearTimers();
  clearAssessTimeout();
  updateUI();
}

function showResultsPage() {
  showView("results");
  const state = conversationState;
  
  // Calculate overall statistics
  let totalRelevance = 0;
  let totalOverall = 0;
  let passedCount = 0;
  let failedCount = 0;
  const questionResults = [];
  
  for (let i = 0; i < state.questions.length; i++) {
    const r = state.assessments[i];
    if (!r) {
      questionResults.push({
        question: i + 1,
        status: "No Result",
        relevance: 0,
        overall: 0,
        message: "Backend not called / failed"
      });
      failedCount++;
      continue;
    }
    
    const relPercent = r.relevancePercent || 0;
    const overallPercent = r.step5?.overallPercent || 0;
    const isValid = r.isValid || false;
    const relStatus = r.relevanceStatus || (relPercent >= 30 ? "Relevant" : "Not Relevant");
    
    totalRelevance += relPercent;
    if (isValid && r.step5) {
      totalOverall += overallPercent;
      passedCount++;
    } else {
      failedCount++;
    }
    
    questionResults.push({
      question: i + 1,
      status: isValid ? "PASS" : "FAIL",
      relevance: relPercent,
      overall: overallPercent,
      message: r.message || "",
      relStatus: relStatus,
      step5: r.step5
    });
  }
  
  const avgRelevance = totalRelevance / state.questions.length;
  const avgOverall = passedCount > 0 ? totalOverall / passedCount : 0;
  const totalScore = `${passedCount}/${state.questions.length}`;
  
  // Update results display
  if (elements.resultStatusText) {
    elements.resultStatusText.textContent = passedCount === state.questions.length ? "PASSED" : "PARTIAL";
  }
  
  if (elements.resultMarksText) {
    elements.resultMarksText.textContent = totalScore;
  }
  
  if (elements.resultPercentage) {
    elements.resultPercentage.textContent = `Average Overall Score: ${avgOverall.toFixed(1)}%`;
  }
  
  // Show simplified results - only FAIL or Overall Percentage
  if (elements.detailedResults) {
    let html = "<h3>Question-wise Results</h3>";
    questionResults.forEach(qr => {
      html += `<div class="result-item">`;
      html += `<div>`;
      html += `<div class="result-item-label">Question ${qr.question}</div>`;
      html += `</div>`;
      html += `<div style="text-align: right;">`;
      // Show FAIL if relevance didn't pass, otherwise show overall percentage
      if (qr.status === "FAIL" || qr.relevance < 30 || !qr.step5) {
        html += `<div class="result-item-value" style="color: #dc3545; font-size: 1.5em;">FAIL</div>`;
      } else {
        html += `<div class="result-item-value" style="font-size: 1.5em;">${qr.overall.toFixed(1)}%</div>`;
      }
      html += `</div>`;
      html += `</div>`;
    });
    elements.detailedResults.innerHTML = html;
  }
}

function restartTest() {
  // Reset state
  conversationState.currentState = SessionState.INIT;
  conversationState.currentQuestionIndex = 0;
  conversationState.questionTimeLeftSec = 0;
  conversationState.isMicOn = false;
  conversationState.recordings = [];
  conversationState.assessments = [];
  conversationState.repeatUsed = {};
  
  // Clear timers
  clearTimers();
  clearAssessTimeout();
  
  // Stop any ongoing recording
  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    try {
      mediaRecorder.stop();
    } catch (e) {}
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  stopLiveTranscript();
  
  // Show rules page
  showView("rules");
  updateUI();
}

// Make restartTest available globally
window.restartTest = restartTest;

function goToNextQuestion() {
  const state = conversationState;
  const isLastQuestion = state.currentQuestionIndex >= state.questions.length - 1;
  
  if (isLastQuestion) {
    // All questions completed
    state.currentState = SessionState.END;
    clearTimers();
    clearAssessTimeout();
    updateUI();
    return;
  }
  
  // Move to next question
  state.currentQuestionIndex += 1;
  state.currentState = SessionState.AVATAR_SPEAKING;
  state.isMicOn = false;
  state.questionTimeLeftSec = 0;
  
  // Reset repeat flag for new question
  state.repeatUsed[state.currentQuestionIndex] = false;
  
  playAvatarQuestionAudio();
  updateUI();
}

if (elements.beginTestBtn) {
elements.beginTestBtn.addEventListener("click", async () => {
  const ok = await ensureMicPermission();
  if (!ok) return;
  // Ask anything related to mic/transcript permission here (one time).
  prewarmSpeechRecognitionPermission();
  showView("test");
  if (conversationState.currentState === SessionState.INIT) {
    startSession();
  }
});
}

if (elements.startMicBtn) elements.startMicBtn.addEventListener("click", startMic);
if (elements.stopMicBtn) elements.stopMicBtn.addEventListener("click", stopMic);
if (elements.nextQuestionBtn) elements.nextQuestionBtn.addEventListener("click", goToNextQuestion);
if (elements.repeatQuestionBtn) elements.repeatQuestionBtn.addEventListener("click", () => {
  const state = conversationState;
  // Enable repeat only before the user starts mic
  if (state.currentState !== SessionState.USER_SPEAKING || state.isMicOn) return;
  if (state.currentQuestionIndex < 0 || state.currentQuestionIndex >= state.questions.length) return;
  if (conversationState.repeatUsed[state.currentQuestionIndex]) return;

  // Mark repeat as used for this question to prevent further repeats
  conversationState.repeatUsed[state.currentQuestionIndex] = true;

  // Replay question using avatar speaking state, then return to USER_SPEAKING on end
  const q = state.questions[state.currentQuestionIndex];
  conversationState.currentState = SessionState.AVATAR_SPEAKING;
  updateUI();
  speakQuestion(q.text, { notifyOnEnd: true });
});

// Initialize - show rules page
showView("rules");
updateUI();


