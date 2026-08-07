const statusEl = document.getElementById("status");

const startScreenEl = document.getElementById("start-screen");
const startSessionBtn = document.getElementById("start-session-btn");

const module1El = document.getElementById("module-1");
const patternNameEl = document.getElementById("pattern-name");
const patternRuleEl = document.getElementById("pattern-rule");
const patternIpaEl = document.getElementById("pattern-ipa");
const patternFamilyEl = document.getElementById("pattern-family");
const speedSlowBtn = document.getElementById("speed-slow-btn");
const speedNormalBtn = document.getElementById("speed-normal-btn");
const speedFastBtn = document.getElementById("speed-fast-btn");
const listenPatternBtn = document.getElementById("listen-pattern-btn");
const practicePatternBtn = document.getElementById("practice-pattern-btn");
const nextToModule2Btn = document.getElementById("next-to-module-2-btn");

const module2El = document.getElementById("module-2");
const chunkTextEl = document.getElementById("chunk-text");
const chunkFunctionEl = document.getElementById("chunk-function");
const listenChunkBtn = document.getElementById("listen-chunk-btn");
const recordChunkBtn = document.getElementById("record-chunk-btn");
const chunkFeedbackEl = document.getElementById("chunk-feedback");
const chunkExamplesStatusEl = document.getElementById("chunk-examples-status");
const chunkExampleSentenceEl = document.getElementById("chunk-example-sentence");
const chunkExampleParagraphEl = document.getElementById("chunk-example-paragraph");
const chunkExampleConversationEl = document.getElementById("chunk-example-conversation");
const nextToModule3Btn = document.getElementById("next-to-module-3-btn");

const module3El = document.getElementById("module-3");
const conversationStartersEl = document.getElementById("conversation-starters");
const linkingWordsEl = document.getElementById("linking-words");
const topicSuggestionsEl = document.getElementById("topic-suggestions");
const recordBtn = document.getElementById("record-btn");
const chatLogEl = document.getElementById("chat-log");

let sessionId = null;
let todaysPlan = null;
let history = [];
let mediaRecorder = null;
let audioChunks = [];
let recording = false;
let recordingMode = null; // "pattern" | "chunk" | "free"

// El usuario reportó que módulo 1 reproducía las palabras "super rápido" —
// pidió elegir entre lento/normal/rápido. 0.7/1/1.3 son valores típicos de
// apps de pronunciación (Duolingo-style), no vienen de una API.
const SPEED_VALUES = { slow: 0.7, normal: 1, fast: 1.3 };
let playbackSpeed = SPEED_VALUES.normal;

function setSpeed(speed, btn) {
  playbackSpeed = SPEED_VALUES[speed];
  [speedSlowBtn, speedNormalBtn, speedFastBtn].forEach((b) =>
    b.classList.remove("speed-active")
  );
  btn.classList.add("speed-active");
}

speedSlowBtn.addEventListener("click", () => setSpeed("slow", speedSlowBtn));
speedNormalBtn.addEventListener("click", () => setSpeed("normal", speedNormalBtn));
speedFastBtn.addEventListener("click", () => setSpeed("fast", speedFastBtn));

function showModule(el) {
  [module1El, module2El, module3El].forEach((m) => m.classList.add("hidden"));
  el.classList.remove("hidden");
}

async function parseJsonOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseJsonOrThrow(response);
}

async function speak(text) {
  const response = await fetch("/api/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  const audioBlob = await response.blob();
  return URL.createObjectURL(audioBlob);
}

async function playText(text, rate = 1) {
  const url = await speak(text);
  const audio = new Audio(url);
  audio.playbackRate = rate;
  await audio.play();
}

async function playTextWithButton(text, btn, rate = 1) {
  btn.disabled = true;
  try {
    await playText(text, rate);
  } finally {
    btn.disabled = false;
  }
}

async function transcribeAudio(audioBlob, targetWords, patternName) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.webm");
  if (targetWords && targetWords.length) {
    formData.append("target_words", targetWords.join(","));
  }
  if (patternName) {
    formData.append("pattern_name", patternName);
  }
  const response = await fetch("/api/transcribe", { method: "POST", body: formData });
  return parseJsonOrThrow(response);
}

async function startSession() {
  statusEl.textContent = "Loading today's plan...";
  todaysPlan = await (await fetch("/api/today")).json();
  const started = await postJson("/api/session/start", { topic: "" });
  sessionId = started.session_id;

  const pattern = todaysPlan.pattern_focus;
  if (pattern) {
    patternNameEl.textContent = pattern.name;
    patternRuleEl.textContent = pattern.rule_es;
    patternIpaEl.textContent = pattern.rule_ipa;
    patternFamilyEl.innerHTML = renderPatternFamily(pattern.family, pattern.family_stress, pattern.family_respelling);
  }
  const chunk = todaysPlan.chunk_today;
  if (chunk) {
    chunkTextEl.textContent = chunk.chunk;
    chunkFunctionEl.textContent = chunk.function;
  }
  conversationStartersEl.textContent = (todaysPlan.conversation_starters || []).join(" · ");
  linkingWordsEl.textContent = (todaysPlan.linking_words || []).join(", ");
  topicSuggestionsEl.textContent = (todaysPlan.topic_options || []).join(" · ");

  startScreenEl.classList.add("hidden");
  statusEl.textContent = "";
  showModule(module1El);
}

const AUTO_STOP_MS = { pattern: 4000, chunk: 5000 };
const BUTTON_FOR_MODE = {
  pattern: practicePatternBtn,
  chunk: recordChunkBtn,
  free: recordBtn,
};
const IDLE_LABEL = {
  pattern: "🎙️ Record my attempt",
  chunk: "🎙️ Use it in a sentence",
  free: "🎙️ Record",
};

async function startRecording(mode) {
  if (!navigator.mediaDevices) {
    statusEl.textContent =
      "Error: the microphone only works over HTTPS or localhost. Over WiFi (http://IP:8000) the browser blocks it.";
    return;
  }
  recordingMode = mode;
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];
  mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
  mediaRecorder.onstop = handleRecordingStop;
  mediaRecorder.start();
  recording = true;

  const btn = BUTTON_FOR_MODE[mode];
  if (mode === "free") {
    btn.textContent = "⏹️ Stop (tap to stop)";
  } else {
    btn.disabled = true;
    btn.textContent = "🔴 Recording... (stops automatically)";
  }
  statusEl.textContent = "Recording...";

  if (AUTO_STOP_MS[mode]) {
    setTimeout(() => {
      if (recording) stopRecording();
    }, AUTO_STOP_MS[mode]);
  }
}

function stopRecording() {
  mediaRecorder.stop();
  recording = false;
  const btn = BUTTON_FOR_MODE[recordingMode];
  btn.disabled = false;
  btn.textContent = IDLE_LABEL[recordingMode];
}

async function handleRecordingStop() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  try {
    if (recordingMode === "pattern") {
      await handlePatternRecording(audioBlob);
    } else if (recordingMode === "chunk") {
      await handleChunkRecording(audioBlob);
    } else {
      await handleFreeConversationRecording(audioBlob);
    }
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// ~x~ = silent letter/syllable, *x* = highlighted (pronounced differently
// than written, but not silent) -- markup added by seed.py for pattern
// example words.
function stripMarkup(word) {
  return word.replace(/[~*]/g, "");
}

function renderMarkedWord(word) {
  return word
    .split(/(~[^~]+~|\*[^*]+\*)/g)
    .map((part) => {
      if (part.startsWith("~") && part.endsWith("~")) {
        return `<s>${escapeHtml(part.slice(1, -1))}</s>`;
      }
      if (part.startsWith("*") && part.endsWith("*")) {
        return `<mark>${escapeHtml(part.slice(1, -1))}</mark>`;
      }
      return escapeHtml(part);
    })
    .join("");
}

function renderPatternFamily(family, familyStress, familyRespelling) {
  return family
    .map((word, i) => {
      const marked = renderMarkedWord(word);
      const stress = familyStress ? familyStress[i] : null;
      const respelling = familyRespelling ? familyRespelling[i] : null;
      const extras = [stress, respelling].filter(Boolean);
      if (!extras.length) return marked;
      return `${marked} <small>(${extras.map(escapeHtml).join(" · ")})</small>`;
    })
    .join(", ");
}

function stripMarkdown(text) {
  return text
    .replace(/\*\*(.*?)\*\*/g, "$1")
    .replace(/__(.*?)__/g, "$1")
    .replace(/\*(.*?)\*/g, "$1")
    .replace(/_(.*?)_/g, "$1")
    .replace(/`(.*?)`/g, "$1")
    .trim();
}

function boldChunkOccurrences(text, chunk) {
  const escapedText = escapeHtml(text);
  const chunkCore = chunk.trim().replace(/[.!?]+$/, "");
  const escapedChunk = escapeHtml(chunkCore).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  if (!escapedChunk) return escapedText;
  return escapedText.replace(new RegExp(escapedChunk, "gi"), (match) => `<strong>${match}</strong>`);
}

async function loadChunkExamples() {
  chunkExamplesStatusEl.textContent = "Loading examples...";
  try {
    const examples = await postJson("/api/chunk-examples", {
      chunk: todaysPlan.chunk_today.chunk,
      function: todaysPlan.chunk_today.function,
    });
    const chunk = todaysPlan.chunk_today.chunk;
    chunkExampleSentenceEl.innerHTML = boldChunkOccurrences(examples.sentence, chunk);
    chunkExampleParagraphEl.innerHTML = boldChunkOccurrences(examples.paragraph, chunk);
    chunkExampleConversationEl.innerHTML = boldChunkOccurrences(examples.conversation, chunk);
    chunkExamplesStatusEl.textContent = "";
  } catch (error) {
    chunkExamplesStatusEl.textContent = `Couldn't load the examples: ${error.message}`;
  }
}

async function handlePatternRecording(audioBlob) {
  statusEl.textContent = "Transcribing...";
  const targetWords = todaysPlan.pattern_focus.family.map(stripMarkup);
  const transcript = await transcribeAudio(audioBlob, targetWords, todaysPlan.pattern_focus.name);
  await postJson("/api/log", {
    session_id: sessionId,
    event: "pattern_practiced",
    pattern_id: todaysPlan.pattern_focus.id,
    stress_results: transcript.stress_results,
    phoneme_errors: transcript.phoneme_errors,
    phoneme_evaluated: transcript.phoneme_evaluated,
  });
  const results = transcript.stress_results || [];
  if (results.length) {
    const correct = results.filter((r) => r.correct).length;
    const incorrect = results.filter((r) => !r.correct).map((r) => r.word);
    statusEl.textContent = incorrect.length
      ? `Stress correct on ${correct}/${results.length} word(s) — check: ${incorrect.join(", ")}.`
      : `Nice! Stress correct on ${correct}/${results.length} word(s).`;
  } else {
    statusEl.textContent = `I heard: "${transcript.text}" — try saying one of the words above so I can check your stress.`;
  }
  nextToModule2Btn.classList.remove("hidden");
}

async function handleChunkRecording(audioBlob) {
  statusEl.textContent = "Transcribing...";
  const transcript = await transcribeAudio(audioBlob);
  const result = await postJson("/api/log", {
    session_id: sessionId,
    event: "chunk_used",
    chunk: todaysPlan.chunk_today.chunk,
    transcript: transcript.text,
  });
  if (result.produced) {
    chunkFeedbackEl.textContent = "Nice! You used the chunk.";
    nextToModule3Btn.classList.remove("hidden");
  } else {
    chunkFeedbackEl.textContent = `You said: "${transcript.text}" — I didn't catch the exact chunk. Try recording it again.`;
  }
  statusEl.textContent = "";
}

function appendChatMessage(text, sender, audioUrl) {
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble chat-${sender}`;
  const textEl = document.createElement("p");
  textEl.textContent = text;
  bubble.appendChild(textEl);
  if (audioUrl) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = audioUrl;
    bubble.appendChild(audio);
  }
  chatLogEl.appendChild(bubble);
  chatLogEl.scrollTop = chatLogEl.scrollHeight;
  return bubble;
}

async function handleFreeConversationRecording(audioBlob) {
  statusEl.textContent = "Transcribing...";
  const targetWords = (todaysPlan.week_words || []).map((w) => w.form);
  const transcript = await transcribeAudio(audioBlob, targetWords);
  appendChatMessage(transcript.text, "user");

  statusEl.textContent = "Thinking...";
  const tutor = await postJson("/api/tutor", {
    text: transcript.text, history, session_id: sessionId,
    wpm: transcript.wpm, fillers: transcript.fillers,
    stress_results: transcript.stress_results,
  });
  sessionId = tutor.session_id;
  const cleanReply = stripMarkdown(tutor.reply);
  history.push({ role: "user", content: transcript.text });
  history.push({ role: "assistant", content: cleanReply });

  if (todaysPlan.chunk_today) {
    postJson("/api/log", {
      session_id: sessionId,
      event: "chunk_spontaneous",
      chunk: todaysPlan.chunk_today.chunk,
      transcript: transcript.text,
    }).catch(() => {});
  }
  if ((todaysPlan.week_words || []).length) {
    postJson("/api/log", {
      session_id: sessionId,
      event: "words_used",
      transcript: transcript.text,
      week_words: todaysPlan.week_words,
    }).catch(() => {});
  }

  statusEl.textContent = "Generating audio...";
  const audioUrl = await speak(cleanReply);
  const tutorBubble = appendChatMessage(cleanReply, "tutor", audioUrl);
  tutorBubble.querySelector("audio").play();
  statusEl.textContent = "Done.";
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js").catch((error) => {
    console.error("Service worker registration failed:", error);
  });
}

startSessionBtn.addEventListener("click", () => {
  startSession().catch((error) => {
    statusEl.textContent = `Error: ${error.message}`;
  });
});

listenPatternBtn.addEventListener("click", () => {
  const cleanWords = todaysPlan.pattern_focus.family.map(stripMarkup);
  playTextWithButton(cleanWords.join(". "), listenPatternBtn, playbackSpeed).catch((error) => {
    statusEl.textContent = `Error: ${error.message}`;
  });
});

practicePatternBtn.addEventListener("click", () => startRecording("pattern"));

nextToModule2Btn.addEventListener("click", () => {
  showModule(module2El);
  loadChunkExamples();
});

listenChunkBtn.addEventListener("click", () => {
  playTextWithButton(todaysPlan.chunk_today.chunk, listenChunkBtn).catch((error) => {
    statusEl.textContent = `Error: ${error.message}`;
  });
});

recordChunkBtn.addEventListener("click", () => startRecording("chunk"));

nextToModule3Btn.addEventListener("click", () => showModule(module3El));

recordBtn.addEventListener("click", async () => {
  try {
    if (recording) {
      stopRecording();
    } else {
      await startRecording("free");
    }
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
});
