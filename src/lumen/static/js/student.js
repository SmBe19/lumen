"use strict";

(function () {
  const app = document.getElementById("student-app");
  if (!app) return;

  let T = {};
  const stringsEl = document.getElementById("i18n-strings");
  if (stringsEl) {
    try {
      T = JSON.parse(stringsEl.textContent || "{}");
    } catch (e) {
      T = {};
    }
  }

  function _(key, params) {
    let text = Object.prototype.hasOwnProperty.call(T, key) ? T[key] : key;
    if (params) {
      Object.keys(params).forEach(function (name) {
        text = text.split("%(" + name + ")s").join(params[name]);
      });
    }
    return text;
  }

  const examKey = app.dataset.examKey;
  const configUrl = "/api/exam/" + encodeURIComponent(examKey) + "/config";
  const screenshotUrl = "/api/exam/" + encodeURIComponent(examKey) + "/screenshot";
  const logUrl = "/api/exam/" + encodeURIComponent(examKey) + "/log";

  const state = {
    name: "",
    interval: parseInt(app.dataset.interval || "10", 10) || 10,
    scale: parseFloat(app.dataset.scale || "0.5") || 0.5,
    recording: app.dataset.recording === "true",
    sharing: false,
    stream: null,
    track: null,
    captureInFlight: false,
    timer: null,
    shareEndedHandled: false,
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
  const preview = document.getElementById("preview");
  const messages = document.getElementById("student-messages");

  const steps = [stepName, stepShare, stepStatus].filter(Boolean);

  function showStep(step) {
    steps.forEach(function (element) {
      element.classList.add("hidden");
    });
    if (step) step.classList.remove("hidden");
  }

  // Replace the previous notice so only the current status is shown.
  function showMessage(text, kind) {
    if (!messages) return;
    messages.innerHTML = "";
    if (!text) return;
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
        showMessage(_("js.select_name_first"), "warn");
        return;
      }
      state.name = value;
      requestNotifications();
      showStep(stepShare);
      setStatus();
    });
  }

  // ---- Step 2/3: screen sharing ------------------------------------------
  function setStatus() {
    // Keep the browser tab title in sync with whether recording works.
    document.title = state.sharing && state.recording
      ? _("student.title_recording")
      : _("student.title_not_recording");
    if (!statusText) return;
    if (!state.sharing) {
      statusText.textContent = _("student.status_not_sharing");
      statusText.className = "muted";
      return;
    }
    if (state.recording) {
      statusText.textContent = _("js.status_recording_ok");
      statusText.className = "ok-text";
    } else {
      statusText.textContent = _("js.status_recording_stopped");
      statusText.className = "error-text";
    }
  }

  async function startSharing() {
    if (!state.name) {
      showMessage(_("js.select_name_first"), "warn");
      return;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      showMessage(_("js.sharing_not_available"), "error");
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "monitor",
          selfBrowserSurface: "exclude",
          surfaceSwitching: "exclude",
        },
        audio: false,
      });
    } catch (error) {
      if (error && error.name === "NotAllowedError") {
        showMessage(_("js.share_cancelled"), "warn");
      } else {
        showMessage(
          _("js.could_not_start", { error: (error && error.message) || "" }),
          "error"
        );
      }
      return;
    }

    const track = stream.getVideoTracks()[0];
    const settings = track.getSettings ? track.getSettings() : {};
    const surface = settings.displaySurface;

    if (surface && surface !== "monitor") {
      stream.getTracks().forEach(function (t) { t.stop(); });
      showMessage(_("js.wrong_surface", { surface: surface }), "error");
      sendLog("error", "shared " + surface + " instead of monitor");
      return;
    }

    state.stream = stream;
    state.track = track;
    state.sharing = true;
    state.shareEndedHandled = false;
    if (preview) preview.srcObject = stream;
    track.addEventListener("ended", onShareEnded);

    showStep(stepStatus);
    setStatus();
    sendLog("start_sharing", surface || "unknown displaySurface");
    scheduleNext();
  }

  // Called exactly once per sharing session.
  function onShareEnded() {
    if (!state.sharing || state.shareEndedHandled) return;
    state.shareEndedHandled = true;
    state.sharing = false;
    state.stream = null;
    state.track = null;
    if (preview) preview.srcObject = null;
    setStatus();
    showStep(stepShare);
    showMessage(_("js.share_ended"), "error");
    notify(_("js.notify_stopped_title"), _("js.notify_stopped_body"));
    sendLog("stop_sharing", "screen share track ended");
  }

  function stopSharing() {
    // Stopping while recording must be deliberate: ask for confirmation.
    if (state.recording && !window.confirm(_("js.stop_confirm"))) return;
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
    if (!preview) return;

    const settings =
      state.track && state.track.getSettings ? state.track.getSettings() : {};
    const sourceWidth = preview.videoWidth || settings.width || 0;
    const sourceHeight = preview.videoHeight || settings.height || 0;
    if (!sourceWidth || !sourceHeight) return;

    state.captureInFlight = true;
    try {
      canvas.width = Math.max(1, Math.round(sourceWidth * state.scale));
      canvas.height = Math.max(1, Math.round(sourceHeight * state.scale));
      const ctx = canvas.getContext("2d");
      ctx.imageSmoothingEnabled = true;
      if ("imageSmoothingQuality" in ctx) ctx.imageSmoothingQuality = "high";
      // Draw the full source frame into the (possibly smaller) canvas so the
      // scale is applied regardless of the captured surface resolution.
      ctx.drawImage(
        preview,
        0,
        0,
        sourceWidth,
        sourceHeight,
        0,
        0,
        canvas.width,
        canvas.height
      );

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
      }
    } catch (error) {
      sendLog("error", "capture failed: " + (error && error.message));
    } finally {
      state.captureInFlight = false;
    }
  }

  // ---- Config polling -----------------------------------------------------
  async function pollConfig() {
    try {
      const response = await fetch(configUrl, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("HTTP " + response.status);
      const data = await response.json();
      if (data.status !== "ok") return;
      const previousInterval = state.interval;
      state.interval = Math.max(1, parseInt(data.interval, 10) || state.interval);
      state.scale = Math.min(1, Math.max(0.01, parseFloat(data.scale) || state.scale));
      const wasRecording = state.recording;
      state.recording = !!data.recording;
      setStatus();
      if (state.sharing && state.recording && !wasRecording) {
        showMessage(_("js.recording_started"), "ok");
        scheduleNext();
      }
      if (state.sharing && !state.recording && wasRecording) {
        showMessage(_("js.recording_stopped"), "warn");
      }
      if (state.sharing && state.recording && state.interval !== previousInterval) {
        scheduleNext();
      }
    } catch (error) {
      /* keep polling */
    }
  }

  // At most one config request every 10 seconds, with jitter to spread load.
  function schedulePoll() {
    const delay = 10000 + Math.random() * 5000;
    setTimeout(function () {
      pollConfig().finally(schedulePoll);
    }, delay);
  }

  // ---- Leave warning ------------------------------------------------------
  window.addEventListener("beforeunload", function (event) {
    if (state.sharing) {
      event.preventDefault();
      event.returnValue = _("js.leave_warning");
      return event.returnValue;
    }
  });

  pollConfig();
  schedulePoll();
  setStatus();
})();
