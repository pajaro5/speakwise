const statusEl = document.getElementById("status");

const startScreenEl = document.getElementById("start-screen");
const startSessionBtn = document.getElementById("start-session-btn");

const module1El = document.getElementById("module-1");
const patternNameEl = document.getElementById("pattern-name");
const patternRuleEl = document.getElementById("pattern-rule");
const patternIpaEl = document.getElementById("pattern-ipa");
const patternFamilyEl = document.getElementById("pattern-family");
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
const transcriptEl = document.getElementById("transcript");
const tutorReplyEl = document.getElementById("tutor-reply");
const tutorAudioEl = document.getElementById("tutor-audio");

let sessionId = null;
let todaysPlan = null;
let history = [];
let mediaRecorder = null;
let audioChunks = [];
let recording = false;
let recordingMode = null; // "pattern" | "chunk" | "free"

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

async function playText(text) {
  const url = await speak(text);
  const audio = new Audio(url);
  await audio.play();
}

async function playTextWithButton(text, btn) {
  btn.disabled = true;
  try {
    await playText(text);
  } finally {
    btn.disabled = false;
  }
}

async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.webm");
  const response = await fetch("/api/transcribe", { method: "POST", body: formData });
  return parseJsonOrThrow(response);
}

async function startSession() {
  statusEl.textContent = "Cargando el plan de hoy...";
  todaysPlan = await (await fetch("/api/today")).json();
  const started = await postJson("/api/session/start", { topic: "" });
  sessionId = started.session_id;

  const pattern = todaysPlan.pattern_focus;
  if (pattern) {
    patternNameEl.textContent = pattern.name;
    patternRuleEl.textContent = pattern.rule_es;
    patternIpaEl.textContent = pattern.rule_ipa;
    patternFamilyEl.textContent = pattern.family.join(", ");
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
  pattern: "🎙️ Grabar mi intento",
  chunk: "🎙️ Usarlo en una oración",
  free: "🎙️ Grabar",
};

async function startRecording(mode) {
  if (!navigator.mediaDevices) {
    statusEl.textContent =
      "Error: el micrófono solo funciona en HTTPS o localhost. Por WiFi (http://IP:8000) el navegador lo bloquea.";
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
    btn.textContent = "⏹️ Detener (tocá para parar)";
  } else {
    btn.disabled = true;
    btn.textContent = "🔴 Grabando... (se detiene solo)";
  }
  statusEl.textContent = "Grabando...";

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

function boldChunkOccurrences(text, chunk) {
  const escapedText = escapeHtml(text);
  const chunkCore = chunk.trim().replace(/[.!?]+$/, "");
  const escapedChunk = escapeHtml(chunkCore).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  if (!escapedChunk) return escapedText;
  return escapedText.replace(new RegExp(escapedChunk, "gi"), (match) => `<strong>${match}</strong>`);
}

async function loadChunkExamples() {
  chunkExamplesStatusEl.textContent = "Cargando ejemplos...";
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
    chunkExamplesStatusEl.textContent = `No se pudieron cargar los ejemplos: ${error.message}`;
  }
}

async function handlePatternRecording(audioBlob) {
  statusEl.textContent = "Transcribiendo...";
  await transcribeAudio(audioBlob); // solo confirma que se grabó algo, no hay scoring todavia
  await postJson("/api/log", {
    session_id: sessionId,
    event: "pattern_practiced",
    pattern_id: todaysPlan.pattern_focus.id,
  });
  statusEl.textContent = "¡Practicado!";
  nextToModule2Btn.classList.remove("hidden");
}

async function handleChunkRecording(audioBlob) {
  statusEl.textContent = "Transcribiendo...";
  const transcript = await transcribeAudio(audioBlob);
  const result = await postJson("/api/log", {
    session_id: sessionId,
    event: "chunk_used",
    chunk: todaysPlan.chunk_today.chunk,
    transcript: transcript.text,
  });
  chunkFeedbackEl.textContent = result.produced
    ? "¡Bien! Usaste el chunk."
    : `Dijiste: "${transcript.text}" — no detecté el chunk exacto, pero seguimos igual.`;
  statusEl.textContent = "";
  nextToModule3Btn.classList.remove("hidden");
}

async function handleFreeConversationRecording(audioBlob) {
  statusEl.textContent = "Transcribiendo...";
  const transcript = await transcribeAudio(audioBlob);
  transcriptEl.textContent = transcript.text;

  statusEl.textContent = "Pensando...";
  const tutor = await postJson("/api/tutor", {
    text: transcript.text, history, session_id: sessionId,
    wpm: transcript.wpm, fillers: transcript.fillers,
  });
  tutorReplyEl.textContent = tutor.reply;
  sessionId = tutor.session_id;
  history.push({ role: "user", content: transcript.text });
  history.push({ role: "assistant", content: tutor.reply });

  statusEl.textContent = "Generando audio...";
  const audioUrl = await speak(tutor.reply);
  tutorAudioEl.src = audioUrl;
  tutorAudioEl.play();
  statusEl.textContent = "Listo.";
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js").catch((error) => {
    console.error("No se pudo registrar el service worker:", error);
  });
}

startSessionBtn.addEventListener("click", () => {
  startSession().catch((error) => {
    statusEl.textContent = `Error: ${error.message}`;
  });
});

listenPatternBtn.addEventListener("click", () => {
  playTextWithButton(todaysPlan.pattern_focus.family.join(". "), listenPatternBtn).catch((error) => {
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
