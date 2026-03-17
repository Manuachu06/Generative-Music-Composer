const generatedTracks = [];
let latestTrackId = null;

function splitCsv(value) {
  return value.split(",").map((x) => x.trim()).filter(Boolean);
}

async function request(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

function setJobState(text, isError = false) {
  const node = document.getElementById("job-state");
  node.textContent = text;
  node.style.color = isError ? "#fca5a5" : "#93c5fd";
}

function renderTrackList() {
  const list = document.getElementById("track-list");
  if (generatedTracks.length === 0) {
    list.innerHTML = '<p class="muted">No tracks yet.</p>';
    return;
  }

  list.innerHTML = generatedTracks
    .map(
      (track) => `
      <button class="track-item" data-src="${track.audio_url}" data-id="${track.track_id}">
        <strong>${track.track_id}</strong>
        <span>${track.mood} • ${track.theme}</span>
      </button>
    `,
    )
    .join("");

  list.querySelectorAll(".track-item").forEach((item) => {
    item.addEventListener("click", () => {
      const src = item.getAttribute("data-src");
      const id = item.getAttribute("data-id");
      const player = document.getElementById("audio-player");
      player.src = src;
      player.play();
      document.getElementById("current-track").textContent = `Playing ${id}`;
      document.querySelector('#feedback-form input[name="track_id"]').value = id;
    });
  });
}

async function pollUntilDone(jobId) {
  setJobState(`Job ${jobId} submitted. Waiting for completion...`);
  for (let i = 0; i < 25; i += 1) {
    const statusResult = await request(`/v1/music/jobs/${jobId}`);
    const status = statusResult.data.status;

    if (status === "SUCCESS" || status === "completed_local") {
      const result = statusResult.data.result || statusResult.data;
      const audioUrl = result.audio_url || result.audio_uri;

      generatedTracks.unshift({
        track_id: result.track_id,
        mood: result.mood || "unknown",
        theme: result.theme || "unknown",
        audio_url: audioUrl,
      });
      latestTrackId = result.track_id;

      const player = document.getElementById("audio-player");
      player.src = audioUrl;
      document.getElementById("current-track").textContent = `Playing ${result.track_id}`;
      document.querySelector('#feedback-form input[name="track_id"]').value = result.track_id;
      renderTrackList();
      setJobState(`Completed. Track ${result.track_id} is ready.`);
      return;
    }

    if (status === "FAILURE") {
      setJobState(`Job failed: ${JSON.stringify(statusResult.data)}`, true);
      return;
    }

    setJobState(`Job ${jobId} status: ${status}. Retrying...`);
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
  setJobState("Timed out waiting for generation result.", true);
function toPretty(data) {
  return JSON.stringify(data, null, 2);
}

async function request(url, options) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({ error: "Invalid JSON response" }));
  return { ok: response.ok, status: response.status, data };
}

function splitCsv(value) {
  return value
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);
}

document.getElementById("generate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const btn = document.getElementById("generate-btn");
  btn.disabled = true;
  setJobState("Submitting generation request...");

  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    text: form.get("text"),
    audio_uri: form.get("audio_uri") || null,
    duration_sec: Number(form.get("duration_sec")),
    metadata: { source: "product-ui" },
    metadata: { source: "frontend" },
  };

  const result = await request("/v1/music/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!result.ok) {
    setJobState(`Submission failed: ${JSON.stringify(result.data)}`, true);
    btn.disabled = false;
    return;
  }

  await pollUntilDone(result.data.job_id);
  btn.disabled = false;
  document.getElementById("generate-output").textContent = toPretty(result);
});

document.getElementById("status-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const jobId = form.get("job_id");
  const result = await request(`/v1/music/jobs/${jobId}`);
  document.getElementById("status-output").textContent = toPretty(result);
});

document.getElementById("preferences-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const generateForm = new FormData(document.getElementById("generate-form"));
  const userId = generateForm.get("user_id");
  const form = new FormData(event.target);
  const payload = {
    user_id: userId,
  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    genres: splitCsv(form.get("genres")),
    moods: splitCsv(form.get("moods")),
    instruments: splitCsv(form.get("instruments")),
    target_bpm: Number(form.get("target_bpm")),
  };
  const res = await request("/v1/preferences", {

  const result = await request("/v1/preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setJobState(res.ok ? "Preferences saved." : "Failed to save preferences", !res.ok);
});

document.getElementById("recommend-btn").addEventListener("click", async () => {
  const form = new FormData(document.getElementById("generate-form"));
  const userId = form.get("user_id");
  const res = await request(`/v1/recommendations?user_id=${encodeURIComponent(userId)}`);
  document.getElementById("recommend-output").textContent = JSON.stringify(res.data, null, 2);
  document.getElementById("preferences-output").textContent = toPretty(result);
});

document.getElementById("recommend-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const userId = form.get("user_id");
  const result = await request(`/v1/recommendations?user_id=${encodeURIComponent(userId)}`);
  document.getElementById("recommend-output").textContent = toPretty(result);
});

document.getElementById("feedback-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  const generateForm = new FormData(document.getElementById("generate-form"));
  const payload = {
    user_id: generateForm.get("user_id"),
    track_id: form.get("track_id") || latestTrackId || "track_unknown",
    completion: Number(form.get("completion")),
    liked: form.get("liked") === "on",
    replayed: form.get("replayed") === "on",
    skipped: form.get("skipped") === "on",
  };
  const res = await request("/v1/feedback", {
  const payload = {
    user_id: form.get("user_id"),
    track_id: form.get("track_id"),
    completion: Number(form.get("completion")),
    skipped: form.get("skipped") === "on",
    liked: form.get("liked") === "on",
    replayed: form.get("replayed") === "on",
  };

  const result = await request("/v1/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  setJobState(res.ok ? "Feedback sent." : "Feedback failed", !res.ok);
});

renderTrackList();
  document.getElementById("feedback-output").textContent = toPretty(result);
});
