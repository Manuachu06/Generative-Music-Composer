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
  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    text: form.get("text"),
    audio_uri: form.get("audio_uri") || null,
    duration_sec: Number(form.get("duration_sec")),
    metadata: { source: "frontend" },
  };

  const result = await request("/v1/music/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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
  const form = new FormData(event.target);
  const payload = {
    user_id: form.get("user_id"),
    genres: splitCsv(form.get("genres")),
    moods: splitCsv(form.get("moods")),
    instruments: splitCsv(form.get("instruments")),
    target_bpm: Number(form.get("target_bpm")),
  };

  const result = await request("/v1/preferences", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
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
  document.getElementById("feedback-output").textContent = toPretty(result);
});
