"use strict";

(function () {
  const root = document.getElementById("monitor");
  if (!root) return;

  const examId = root.dataset.examId;
  const refreshMs = parseInt(root.dataset.refresh || "5000", 10);

  const elState = document.getElementById("recording-state");
  const elInterval = document.getElementById("interval");
  const elGrid = document.getElementById("grid");
  const elInactiveCount = document.getElementById("inactive-count");
  const elInactiveList = document.getElementById("inactive-list");
  const elWarnings = document.getElementById("warnings");
  const elIssues = document.getElementById("issues");
  const elUpdated = document.getElementById("updated");
  const btnNotify = document.getElementById("enable-notifications");
  const overlay = document.getElementById("overlay");
  const overlayImage = document.getElementById("overlay-image");

  let lastIssueTs = 0;
  let issueCount = 0;
  let primed = false;

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

  if (btnNotify) {
    btnNotify.addEventListener("click", function () {
      if ("Notification" in window) {
        Notification.requestPermission().then(function (perm) {
          btnNotify.textContent =
            perm === "granted" ? "Notifications enabled" : "Notifications blocked";
        });
      } else {
        btnNotify.textContent = "Notifications unsupported";
      }
    });
  }

  if (overlay) {
    overlay.addEventListener("click", function () {
      overlay.classList.add("hidden");
      if (overlayImage) overlayImage.src = "";
    });
  }

  function showOverlay(src) {
    if (!overlay || !overlayImage) return;
    overlayImage.src = src;
    overlay.classList.remove("hidden");
  }

  function fmtSeconds(value) {
    if (value === null || value === undefined) return "never";
    const s = Math.round(value);
    if (s < 60) return s + "s ago";
    if (s < 3600) return Math.floor(s / 60) + "m ago";
    return Math.floor(s / 3600) + "h ago";
  }

  function imageUrl(dir, filename) {
    return (
      "/teacher/exams/" +
      encodeURIComponent(examId) +
      "/image/" +
      encodeURIComponent(dir) +
      "/" +
      encodeURIComponent(filename)
    );
  }

  function detailUrl(dir) {
    return (
      "/teacher/exams/" +
      encodeURIComponent(examId) +
      "/student/" +
      encodeURIComponent(dir)
    );
  }

  function render(data) {
    elState.textContent = data.recording ? "recording" : "stopped";
    elInterval.textContent = data.interval + "s";
    elUpdated.textContent = "updated " + new Date().toLocaleTimeString();

    // Warnings about duplicate submissions and stopped sharing.
    const warnings = [];
    (data.duplicate_warnings || []).forEach(function (s) {
      warnings.push(
        "Possible multiple machines for " + s.name + " (screenshots arriving faster than the interval)."
      );
    });
    if (warnings.length) {
      elWarnings.innerHTML = warnings
        .map(function (w) {
          return '<div class="notice warn">' + escapeHtml(w) + "</div>";
        })
        .join("");
    } else {
      elWarnings.innerHTML = "";
    }

    elInactiveCount.textContent = data.inactive_students.length;
    elInactiveList.textContent = data.inactive_students.length
      ? data.inactive_students.map(function (s) { return s.name; }).join(", ")
      : "All students are sharing (or there are no students).";

    elGrid.innerHTML = "";
    data.students.forEach(function (student) {
      const card = document.createElement("div");
      card.className = "card";
      if (student.inactive) card.className += " inactive";
      if (student.duplicate_warning) card.className += " duplicate";

      // The name links to the student details.
      const name = document.createElement("div");
      name.className = "name";
      const link = document.createElement("a");
      link.href = detailUrl(student.dir);
      link.textContent = student.name;
      name.appendChild(link);
      if (student.inactive) {
        const badge = document.createElement("span");
        badge.className = "badge warn";
        badge.textContent = "not sharing";
        name.appendChild(badge);
      }
      if (student.duplicate_warning) {
        const badge = document.createElement("span");
        badge.className = "badge danger";
        badge.textContent = "multiple?";
        name.appendChild(badge);
      }
      card.appendChild(name);

      // Clicking the screenshot opens a large overlay.
      if (student.latest) {
        const src = imageUrl(student.dir, student.latest.filename);
        const img = document.createElement("img");
        img.src = src;
        img.alt = student.name + " latest screenshot";
        img.addEventListener("click", function () { showOverlay(src); });
        card.appendChild(img);
      } else {
        const placeholder = document.createElement("div");
        placeholder.className = "noimg";
        placeholder.textContent = "no screenshot";
        card.appendChild(placeholder);
      }

      const meta = document.createElement("div");
      meta.className = "muted";
      meta.style.fontSize = "0.8rem";
      meta.textContent =
        "last: " + fmtSeconds(student.seconds_since) + " · " + student.screenshot_count + " total";
      card.appendChild(meta);

      elGrid.appendChild(card);
    });
  }

  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
  }

  function addIssues(issues, recording) {
    if (!issues || !issues.length) return;
    if (issueCount === 0) elIssues.innerHTML = "";
    issues.forEach(function (issue) {
      if (issue.ts <= lastIssueTs) return;
      lastIssueTs = Math.max(lastIssueTs, issue.ts);
      issueCount += 1;
      const li = document.createElement("li");
      const time = new Date(issue.ts * 1000).toLocaleTimeString();
      let label = "error";
      if (issue.event === "stop_sharing") label = "stopped sharing";
      else if (issue.event === "note") label = "note";
      li.textContent =
        time + " - " + issue.dir + " " + label + (issue.message ? ": " + issue.message : "");
      elIssues.insertBefore(li, elIssues.firstChild);
      // Only notify for issues that arrive while recording is active, and
      // only once per issue (not again every time the page is opened).
      if (primed && recording) {
        notify("Lumen", issue.dir + " " + label + (issue.message ? ": " + issue.message : ""));
      }
    });
  }

  function poll() {
    fetch(
      "/teacher/exams/" + encodeURIComponent(examId) + "/data?since=" + lastIssueTs,
      { headers: { Accept: "application/json" } }
    )
      .then(function (response) {
        if (!response.ok) throw new Error("HTTP " + response.status);
        return response.json();
      })
      .then(function (data) {
        render(data);
        addIssues(data.issues, data.recording);
        primed = true;
      })
      .catch(function (error) {
        elUpdated.textContent = "update failed: " + error.message;
      });
  }

  poll();
  setInterval(poll, refreshMs);
})();
