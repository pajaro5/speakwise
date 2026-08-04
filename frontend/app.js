const recordBtn = document.getElementById("record-btn");
const statusEl = document.getElementById("status");
const transcriptEl = document.getElementById("transcript");
const tutorReplyEl = document.getElementById("tutor-reply");
const tutorAudioEl = document.getElementById("tutor-audio");

let mediaRecorder = null;
let audioChunks = [];
let recording = false;
let sessionId = null;
let history = [];

async function startRecording() {
  if (!navigator.mediaDevices) {
    statusEl.textContent =
      "Error: el micrófono solo funciona en HTTPS o localhost. Por WiFi (http://IP:8000) el navegador lo bloquea.";
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];
  mediaRecorder.ondataavailable = (event) => audioChunks.push(event.data);
  mediaRecorder.onstop = handleRecordingStop;
  mediaRecorder.start();
  recording = true;
  recordBtn.textContent = "Detener";
  statusEl.textContent = "Grabando...";
}

function stopRecording() {
  mediaRecorder.stop();
  recording = false;
  recordBtn.textContent = "Grabar";
}

async function handleRecordingStop() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  try {
    statusEl.textContent = "Transcribiendo...";
    const transcript = await transcribeAudio(audioBlob);
    transcriptEl.textContent = transcript.text;

    statusEl.textContent = "Pensando...";
    const tutor = await askTutor(transcript.text, transcript.wpm, transcript.fillers);
    tutorReplyEl.textContent = tutor.reply;
    sessionId = tutor.session_id;
    history.push({ role: "user", content: transcript.text });
    history.push({ role: "assistant", content: tutor.reply });

    statusEl.textContent = "Generando audio...";
    const audioUrl = await speak(tutor.reply);
    tutorAudioEl.src = audioUrl;
    tutorAudioEl.play();
    statusEl.textContent = "Listo.";
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
}

async function parseJsonOrThrow(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `${response.status} ${response.statusText}`);
  }
  return response.json();
}

async function transcribeAudio(audioBlob) {
  const formData = new FormData();
  formData.append("audio", audioBlob, "audio.webm");
  const response = await fetch("/api/transcribe", { method: "POST", body: formData });
  return parseJsonOrThrow(response);
}

async function askTutor(text, wpm, fillers) {
  const response = await fetch("/api/tutor", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, history, session_id: sessionId, wpm, fillers }),
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

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("service-worker.js").catch((error) => {
    console.error("No se pudo registrar el service worker:", error);
  });
}

recordBtn.addEventListener("click", async () => {
  try {
    if (recording) {
      stopRecording();
    } else {
      await startRecording();
    }
  } catch (error) {
    statusEl.textContent = `Error: ${error.message}`;
  }
});
