"use strict";

(function () {
  const app = document.getElementById("student-app");
  if (!app) return;

  const examKey = app.dataset.examKey;
  const configUrl = "/api/exam/" + encodeURIComponent(examKey) + "/config";
  const screenshotUrl = "/api/exam/" + encodeURIComponent(examKey) + "/screenshot";
  const logUrl = "/api/exam/" + encodeURIComponent(examKey) + "/log";

  const state = {
    name: "",
    interval: parseInt(app.dataset.interval || "30", 10) || 30,
    scale: parseFloat(app.dataset.scale || "0.5") || 0.5,
    recording: app.dataset.recording === "true",
    sharing: false,
    stream: null,
    track: null,
    captureInFlight: false,
    lastCapture: 0,
    timer: null,
    loadedAt: Date.now(),
  };
  state.interval = Math.max(1, state.interval);
  state.scale = Math.min(1, Math.max(0.01, state.scale));

  const nameSelect = document.getElementById("student-name");
  const confirmName = document.getElementById("confirm-name");
  const stepName = document.getElementById("step-name");
  const stepShare = document.getElementById("step-share");
  const stepStatus = document.getElementById("step-status");
  const startShare = document.getElementById("start-share");
  const stopShare = document.getElementById("stop-share");
  const statusText = document.getElementById("recording-status");
  const lastUpload = document.getElementById("last-upload");
  const nextUpload = document.getElementById("next-upload");
  const preview = document.getElementById("preview");
  const messages = document.getElementById("student-messages");

  function showMessage(text, kind) {
    const div = document.createElement("div");
    div.className = "notice " + (kind || "warn");
    div.textContent = text;
    messages.appendChild(div);
  }

  function notify(title, body) {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      try {
        new Notification(title, { body: body });
      } catch (e) {
        /* ignore */
      }
    }
  }

  function requestNotifications() {
    if (!("Notification" in window)) return;
    if (Notification.permission === "default") {
      Notification.requestPermission().catch(function () {});
    }
  }

  function sendLog(event, message) {
    if (!state.name) return;
    fetch(logUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: state.name, event: event, message: message || "" }),
    }).catch(function () {});
  }

  // ---- Step 1: choose name ------------------------------------------------
  if (confirmName) {
    confirmName.addEventListener("click", function () {
      const value = nameSelect ? nameSelect.value : "";
      if (!value) {
        showMessage("Please select your name first.", "warn");
        return;
      }
      state.name = value;
      requestNotifications();
      stepName.classList.add("disabled");
      confirmName.disabled = true;
      if (nameSelect) nameSelect.disabled = true;
      stepShare.classList.remove("disabled");
      if (startShare) startShare.disabled = false;
      stepStatus.classList.remove("disabled");
      setStatus();
    });
  }

  // ---- Step 2/3: screen sharing ------------------------------------------
  function setStatus() {
    if (!state.sharing) {
      statusText.textContent = "Not sharing.";
      statusText.className = "muted";
      return;
    }
    if (state.recording) {
      statusText.textContent = "Sharing. Recording is active - screenshots are uploaded every " +
        state.interval + "s.";
      statusText.className = "ok-text";
    } else {
      statusText.textContent = "Sharing. Recording is currently stopped by the teacher.";
      statusText.className = "muted";
    }
  }

  async function startSharing() {
    if (!state.name) {
      showMessage("Please choose your name first.", "warn");
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      showMessage(
        "Screen sharing is not available in this browser or context (it requires a secure HTTPS connection).",
        "error"
      );
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { displaySurface: "monitor" },
        audio: false,
      });
    } catch (error) {
      if (error && error.name === "NotAllowedError") {
        showMessage("Screen sharing was cancelled.", "warn");
      } else {
        showMessage("Could not start screen sharing: " + (error && error.message), "error");
      }
      return;
    }

    const track = stream.getVideoTracks()[0];
    const settings = track.getSettings ? track.getSettings() : {};
    const surface = settings.displaySurface;

    if (surface && surface !== "monitor") {
      stream.getTracks().forEach(function (t) { t.stop(); });
      showMessage(
        "You shared a " + surface + " instead of your entire screen. Please share your whole display.",
        "error"
      );
      sendLog("error", "shared " + surface + " instead of monitor");
      return;
    }

    state.stream = stream;
    state.track = track;
    state.sharing = true;
    preview.srcObject = stream;
    track.addEventListener("ended", onShareEnded);

    startShare.disabled = true;
    stopShare.disabled = false;
    setStatus();
    sendLog("start_sharing", surface || "unknown displaySurface");
    scheduleNext();
  }

  function onShareEnded() {
    if (!state.sharing) return;
    state.sharing = false;
    state.stream = null;
    state.track = null;
    preview.srcObject = null;
    if (startShare) startShare.disabled = false;
    if (stopShare) stopShare.disabled = true;
    setStatus();
    showMessage("Screen sharing stopped. Please start sharing again to continue.", "error");
    notify("Lumen: screen sharing stopped", "Your screen is no longer being recorded.");
    sendLog("stop_sharing", "screen share track ended");
  }

  function stopSharing() {
    if (state.track) {
      try { state.track.stop(); } catch (e) { /* ignore */ }
    }
    onShareEnded();
  }

  if (startShare) startShare.addEventListener("click", startSharing);
  if (stopShare) stopShare.addEventListener("click", stopSharing);

  // ---- Screenshot loop ----------------------------------------------------
  const canvas = document.createElement("canvas");

  function scheduleNext() {
    if (state.timer) clearTimeout(state.timer);
    state.timer = setTimeout(function () {
      capture().finally(scheduleNext);
    }, state.interval * 1000);
  }

  async function capture() {
    if (!state.sharing) return;
    if (!state.recording) return;
    if (state.captureInFlight) return;
    if (!preview.videoWidth || !preview.videoHeight) return;

    state.captureInFlight = true;
    try {
      canvas.width = Math.max(1, Math.round(preview.videoWidth * state.scale));
      canvas.height = Math.max(1, Math.round(preview.videoHeight * state.scale));
      const ctx = canvas.getContext("2d");
      ctx.drawImage(preview, 0, 0, canvas.width, canvas.height);

      const blob = await new Promise(function (resolve) {
        canvas.toBlob(resolve, "image/png");
      });
      if (!blob) return;

      const form = new FormData();
      form.append("name", state.name);
      form.append("screenshot", blob, "screenshot.png");
      const response = await fetch(screenshotUrl, { method: "POST", body: form });
      if (!response.ok) {
        const payload = await response.json().catch(function () { return {}; });
        sendLog("error", "upload failed: " + (payload.message || response.status));
        return;
      }
      state.lastCapture = Date.now();
      lastUpload.textContent = new Date().toLocaleTimeString();
    } catch (error) {
      sendLog("error", "capture failed: " + (error && error.message));
    } finally {
      state.captureInFlight = false;
    }
  }

  // ---- Config polling -----------------------------------------------------
  function pollConfig() {
    fetch(configUrl, { headers: { Accept: "application/json" } })
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        if (data.status !== "ok") return;
        const previousInterval = state.interval;
        state.interval = Math.max(1, parseInt(data.interval, 10) || state.interval);
        state.scale = Math.min(1, Math.max(0.01, parseFloat(data.scale) || state.scale));
        const wasRecording = state.recording;
        state.recording = !!data.recording;
        setStatus();
        if (state.sharing && state.recording && !wasRecording) {
          showMessage("Recording started.", "warn");
          scheduleNext();
        }
        if (state.sharing && !state.recording && wasRecording) {
          showMessage("Recording stopped by the teacher.", "warn");
        }
        if (state.sharing && state.interval !== previousInterval) {
          scheduleNext();
        }
      })
      .catch(function () { /* keep polling */ });
  }

  // ---- Leave warning + countdown -----------------------------------------
  window.addEventListener("beforeunload", function (event) {
    if (state.sharing) {
      event.preventDefault();
      event.returnValue = "Recording is still running.";
      return event.returnValue;
    }
  });

  setInterval(function () {
    if (!state.sharing || !state.recording) {
      nextUpload.textContent = "-";
      return;
    }
    const elapsed = (Date.now() - state.lastCapture) / 1000;
    const remaining = Math.max(0, state.interval - elapsed);
    nextUpload.textContent = Math.ceil(remaining) + "s";
  }, 500);

  pollConfig();
  setInterval(pollConfig, 5000);
  setStatus();
})();
