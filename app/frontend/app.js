const state = {
  generatedTracks: [],
  latestTrackId: null,
  latestVoiceReference: null,
  mediaRecorder: null,
  recordingChunks: [],
  recognition: null,
};

function splitCsv(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

function toPrettyData(items) {
  return items.map((item) => `<span>${item}</span>`).join("");
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({ error: "Invalid JSON response" }));
  return { ok: response.ok, status: response.status, data };
}

function setJobState(text, kind = "info") {
  const node = document.getElementById("job-state");
  node.textContent = text;
  node.dataset.kind = kind;
}

function renderOverview(data) {
  const list = document.getElementById("overview-list");
  list.innerHTML = `
    <div><dt>Product</dt><dd>${data.product_name}</dd></div>
    <div><dt>Voice commands</dt><dd>${data.supports_voice_commands ? "Yes" : "No"}</dd></div>
    <div><dt>Singing reference</dt><dd>${data.supports_singing_reference ? "Yes" : "No"}</dd></div>
    <div><dt>Stores music locally</dt><dd>${data.stores_music_locally ? "Yes" : "No"}</dd></div>
    <div><dt>Modes</dt><dd>${data.generation_modes.join(", ")}</dd></div>
  `;
}

function renderWaveform(peaks = []) {
  const waveform = document.getElementById("waveform");
  if (!peaks.length) {
    waveform.innerHTML = '<p class="muted">Waveform preview appears here.</p>';
    return;
  }

  waveform.innerHTML = peaks
    .map((value) => `<span class="waveform__bar" style="height:${Math.max(10, value * 100)}%"></span>`)
    .join("");
}

function renderTrackHistory() {
  const container = document.getElementById("track-history");
  if (!state.generatedTracks.length) {
    container.innerHTML = '<p class="muted">Generated drafts will appear here.</p>';
    return;
  }

  container.innerHTML = "";
  const template = document.getElementById("history-item-template");

  state.generatedTracks.forEach((track) => {
    const node = template.content.firstElementChild.cloneNode(true);
    node.querySelector(".history-item__title").textContent = track.title;
    node.querySelector(".history-item__meta").textContent = `${track.mood} • ${track.theme} • ${track.duration_sec}s`;
    node.addEventListener("click", () => applyTrackToPlayer(track));
    container.appendChild(node);
  });
}

function applyTrackToPlayer(track) {
  const player = document.getElementById("audio-player");
  player.src = track.audio_data_uri;
  document.getElementById("current-track").classList.remove("empty");
  document.getElementById("current-track").innerHTML = `
    <h3>${track.title}</h3>
    <p>${track.summary}</p>
    <div class="chip-row">${toPrettyData(track.prompt_tags)}</div>
    <dl class="voice-insights">
      <div><dt>Voice mode</dt><dd>${track.voice_insights.performance_type}</dd></div>
      <div><dt>Emotion</dt><dd>${track.voice_insights.emotion}</dd></div>
      <div><dt>Pitch</dt><dd>${track.voice_insights.pitch_signature}</dd></div>
      <div><dt>Storage</dt><dd>${track.storage_mode}</dd></div>
    </dl>
  `;
  renderWaveform(track.waveform_peaks);
  document.querySelector('#feedback-form input[name="track_id"]').value = track.track_id;
  state.latestTrackId = track.track_id;
}

async function pollUntilDone(jobId) {
  for (let attempt = 0; attempt < 25; attempt += 1) {
    const result = await request(`/v1/music/jobs/${jobId}`);
    const status = result.data.status;

    if (status === "SUCCESS" || status === "completed_local") {
      const track = result.data.result || result.data;
      state.generatedTracks.unshift(track);
      applyTrackToPlayer(track);
      renderTrackHistory();
      setJobState(`Draft ready: ${track.title}`, "success");
      return;
    }

    if (status === "FAILURE") {
      setJobState("Generation failed.", "error");
      return;
    }

    setJobState(`Generating… ${status}`, "info");
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }

  setJobState("Timed out waiting for the job result.", "error");
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsDataURL(blob);
  });
}

async function toggleRecorder() {
  const button = document.getElementById("record-btn");
  const statusNode = document.getElementById("recording-status");

  if (state.mediaRecorder && state.mediaRecorder.state === "recording") {
    state.mediaRecorder.stop();
    button.textContent = "Record sung reference";
    statusNode.textContent = "Processing recorded reference…";
    return;
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    statusNode.textContent = "Audio recording is not supported in this browser.";
    return;
  }

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  state.recordingChunks = [];
  state.mediaRecorder = new MediaRecorder(stream);
  state.mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) {
      state.recordingChunks.push(event.data);
    }
  };
  state.mediaRecorder.onstop = async () => {
    const blob = new Blob(state.recordingChunks, { type: state.mediaRecorder.mimeType || "audio/webm" });
    const dataUrl = await blobToDataUrl(blob);
    state.latestVoiceReference = {
      mime_type: blob.type || "audio/webm",
      audio_base64: dataUrl,
      source: "sung-reference",
      transcript_hint: document.getElementById("voice-command-text").value.trim() || null,
    };
    statusNode.textContent = "Sung reference captured. It will be sent with the next generation request.";
    stream.getTracks().forEach((track) => track.stop());
  };

  state.mediaRecorder.start();
  button.textContent = "Stop recording";
  statusNode.textContent = "Recording… sing or hum your idea.";
}

function startSpeechToText() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const target = document.getElementById("voice-command-text");

  if (!SpeechRecognition) {
    target.placeholder = "Speech recognition is not supported in this browser. Type your voice direction here instead.";
    return;
  }

  if (!state.recognition) {
    state.recognition = new SpeechRecognition();
    state.recognition.lang = "en-US";
    state.recognition.interimResults = false;
    state.recognition.maxAlternatives = 1;
    state.recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      target.value = transcript;
      setJobState("Voice command captured.", "success");
    };
    state.recognition.onerror = () => {
      setJobState("Could not capture speech. You can type the instruction instead.", "error");
    };
  }

  state.recognition.start();
  setJobState("Listening for a voice command…", "info");
}

function buildGeneratePayload(form) {
  return {
    user_id: form.get("user_id"),
    text: form.get("text"),
    duration_sec: Number(form.get("duration_sec")),
    context: {
      time_of_day: form.get("time_of_day") || null,
      activity: form.get("activity") || null,
      mood_hint: form.get("mood_hint") || null,
      use_case: form.get("use_case") || null,
    },
    metadata: {
      source: "auralis-studio-ui",
      captured_at: new Date().toISOString(),
    },
    preferences: {
      genres: splitCsv(form.get("genres") || ""),
      moods: splitCsv(form.get("moods") || ""),
      instruments: splitCsv(form.get("instruments") || ""),
      target_bpm: Number(form.get("target_bpm")) || null,
      vocals_allowed: form.get("vocals_allowed") === "on",
    },
    voice_command_text: form.get("voice_command_text") || null,
    voice_reference: state.latestVoiceReference,
    retain_output: form.get("retain_output") === "on",
  };
}

document.getElementById("record-btn").addEventListener("click", toggleRecorder);
document.getElementById("speech-btn").addEventListener("click", startSpeechToText);
document.getElementById("recommend-btn").addEventListener("click", async () => {
  const userId = document.querySelector('#preferences-form input[name="user_id"]').value;
  const result = await request(`/v1/recommendations?user_id=${encodeURIComponent(userId)}`);
  const container = document.getElementById("recommendations");

  if (!result.ok) {
    container.innerHTML = '<p class="muted">Could not load recommendations.</p>';
    return;
  }

  container.innerHTML = result.data.items
    .map(
      (item) => `
        <article class="recommend-card">
          <strong>${item.title}</strong>
          <p>${item.rationale}</p>
          <small>${item.prompt}</small>
          <div class="chip-row">${toPrettyData(item.tags)}</div>
        </article>
      `,
    )
    .join("");
});

document.getElementById("generate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = document.getElementById("generate-btn");
  button.disabled = true;
  setJobState("Submitting generation request…", "info");

  const payload = buildGeneratePayload(new FormData(event.target));
  const result = await request("/v1/music/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!result.ok) {
    setJobState(`Submission failed (${result.status}).`, "error");
    button.disabled = false;
    return;
  }

  await pollUntilDone(result.data.job_id);
  button.disabled = false;
});

document.getElementById("preferences-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    genres: splitCsv(form.get("genres") || ""),
    moods: splitCsv(form.get("moods") || ""),
    instruments: splitCsv(form.get("instruments") || ""),
    target_bpm: Number(form.get("target_bpm")) || null,
    vocals_allowed: form.get("vocals_allowed") === "on",
  };

  const result = await request("/v1/preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  setJobState(result.ok ? "Creator profile saved." : "Could not save profile.", result.ok ? "success" : "error");
});

document.getElementById("feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    track_id: form.get("track_id") || state.latestTrackId || "track_unknown",
    completion: Number(form.get("completion")),
    liked: form.get("liked") === "on",
    replayed: form.get("replayed") === "on",
    skipped: form.get("skipped") === "on",
  };

  const result = await request("/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  setJobState(result.ok ? `Feedback recorded. Reward ${result.data.reward}.` : "Could not save feedback.", result.ok ? "success" : "error");
});

(async function init() {
  renderWaveform([]);
  renderTrackHistory();
  const overview = await request("/v1/product/overview");
  if (overview.ok) {
    renderOverview(overview.data);
  }
})();
