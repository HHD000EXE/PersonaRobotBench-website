/* PersonaRobotBench: no framework, analytics, secrets, or model calls. */
(() => {
  "use strict";

  const FEATURED = [18, 51, 68, 87, 32, 91];
  const PAGE_SIZE = 6;
  const RATES = [1, 2, 4, 8];
  const SKIP_SECONDS = 5;
  const state = { tasks: [], examples: [], category: "All", query: "", visible: PAGE_SIZE, activeExample: 1, rate: 1 };
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];
  const escape = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
  const padded = (id) => String(id).padStart(3, "0");
  const titleFor = (task) => state.examples.find((item) => item.id === task.id)?.shortTitle ?? task.title.replace(/^Personalized\s+/, "");
  const safeUrl = (value) => {
    if (typeof value !== "string" || !value.trim()) return null;
    try {
      const url = new URL(value, window.location.href);
      return ["http:", "https:"].includes(url.protocol) ? url.href : null;
    } catch { return null; }
  };
  const posterFor = (task) => safeUrl(task.preview?.image)
    ?? safeUrl(state.examples.find((item) => item.id === task.id)?.poster);
  const previewAltFor = (task) => task.preview?.alt ?? "Initial simulation scene for " + titleFor(task);
  const schematic = (id) => '<div class="task-schematic" aria-hidden="true"><span class="schematic-number">' + padded(id) + '</span><svg viewBox="0 0 220 150" fill="none" stroke="currentColor" stroke-width=".8"><ellipse cx="110" cy="76" rx="91" ry="48"/><ellipse cx="110" cy="76" rx="48" ry="67" transform="rotate(35 110 76)"/><path d="M0 76h220M110 0v150" stroke-dasharray="3 5"/><circle cx="40" cy="46" r="5" fill="currentColor"/><circle cx="182" cy="104" r="5" fill="currentColor"/><circle cx="110" cy="76" r="13"/></svg></div>';

  function sortedTasks() {
    const rank = (task) => FEATURED.includes(task.id) ? FEATURED.indexOf(task.id) : FEATURED.length + task.id;
    return [...state.tasks].sort((a, b) => rank(a) - rank(b));
  }

  function filteredTasks() {
    const query = state.query.trim().toLowerCase().replace(/^task[\s#-]*/, "");
    return sortedTasks().filter((task) => {
      if (state.category !== "All" && task.category !== state.category) return false;
      if (!query) return true;
      if (/^\d+$/.test(query)) return task.id === Number(query);
      const text = [task.title, task.folder.replaceAll("_", " "), task.instruction, task.category,
        ...task.personas.map((persona) => persona.description)].join(" ").toLowerCase();
      return text.includes(query);
    });
  }

  function card(task) {
    const poster = posterFor(task);
    const figure = poster
      ? '<img src="' + escape(poster) + '" alt="' + escape(previewAltFor(task)) + '" loading="lazy" width="960" height="600">'
      : schematic(task.id);
    const dots = task.personaIds.map((id, index) => '<span class="persona-pill ' + (index % 2 ? "persona-b-color" : "persona-a-color") + '">' + escape(id) + '</span>').join("");
    return '<article class="task-card"><button class="task-card-button" type="button" data-task="' + task.id + '" aria-label="View Task ' + task.id + ': ' + escape(titleFor(task)) + ', ' + task.personaCount + ' persona cases"><div class="task-image">' + figure +
      '<span class="task-number">TASK ' + padded(task.id) + '</span></div><div class="task-card-body"><div class="task-card-heading"><h3>' + escape(titleFor(task)) + '</h3><span class="task-card-arrow" aria-hidden="true">↗</span></div><p>“' + escape(task.instruction) +
      '”</p><div class="task-card-footer"><span class="category">' + escape(task.category) + '</span><span class="persona-dots" aria-label="' + task.personaCount + ' persona cases">' + dots + '</span></div></div></button></article>';
  }

  function renderTasks() {
    const filtered = filteredTasks();
    const visible = filtered.slice(0, state.visible);
    const grid = $("#task-grid");
    if (visible.length) {
      grid.innerHTML = visible.map(card).join("");
    } else {
      grid.innerHTML = '<div class="empty-state"><p>No tasks match this search.</p><button type="button" id="clear-search">Clear search and filters</button></div>';
    }
    $("#task-count").textContent = filtered.length
      ? "Showing " + visible.length + " of " + filtered.length + " tasks"
      : "0 tasks found";
    $("#show-more").hidden = visible.length >= filtered.length;
    $$(".filter-tab").forEach((button) => {
      const selected = button.dataset.filter === state.category;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
  }

  function openTask(id) {
    const task = state.tasks.find((item) => item.id === id);
    if (!task) return;
    const poster = posterFor(task);
    $("#task-dialog-content").innerHTML = '<div class="dialog-cover">' + (poster
      ? '<img src="' + escape(poster) + '" alt="' + escape(previewAltFor(task)) + '" width="960" height="600">'
      : schematic(task.id)) + '</div><div class="dialog-body"><span class="mono small-label">TASK ' + padded(task.id) + " / " + escape(task.category.toUpperCase()) +
      '</span><h2 id="task-dialog-title">' + escape(titleFor(task)) + '</h2><p class="dialog-instruction">“' + escape(task.instruction) +
      '”</p><div class="dialog-personas">' + task.personas.map((persona) => '<div class="dialog-persona"><span class="mono small-label">PERSONA ' + escape(persona.id) +
        '</span><p>' + escape(persona.description) + '</p></div>').join("") +
      '</div><p class="dialog-note">These are authored, task-local persona cases. The scene image is a reference preview; it does not establish a completed policy rollout.' +
      ([20, 21].includes(task.id) ? " This imported task has documented differences and incomplete validation; consult its package notes." : "") +
      '</p></div>';
    const dialog = $("#task-dialog");
    if (typeof dialog.showModal === "function") dialog.showModal();
    else dialog.setAttribute("open", "");
    document.body.classList.add("dialog-open");
  }

  function closeTask() {
    const dialog = $("#task-dialog");
    if (typeof dialog.close === "function") dialog.close();
    else dialog.removeAttribute("open");
    document.body.classList.remove("dialog-open");
  }

  function rolloutCase(example, persona, index) {
    const source = safeUrl(persona.video);
    const poster = safeUrl(persona.videoPoster) ?? safeUrl(example.poster);
    const extension = source ? new URL(source).pathname.toLowerCase().split(".").pop() : "";
    const mime = ({ mp4: "video/mp4", webm: "video/webm" })[extension];
    const visual = source
      ? '<video class="rollout-video" controls playsinline preload="metadata" poster="' + escape(poster ?? "") + '" aria-label="Task ' + example.id + " persona " + escape(persona.id) + ' simulation rollout"><source src="' + escape(source) + '"' + (mime ? ' type="' + mime + '"' : '') + '>Your browser does not support embedded video. <a href="' + escape(source) + '">Download the rollout</a>.</video>'
      : '<div class="video-placeholder" role="img" aria-label="Video placeholder for Task ' + example.id + " persona " + escape(persona.id) +
        '"><img src="' + escape(example.poster) + '" alt="" loading="lazy" width="960" height="600"><span class="video-placeholder-label">PERSONA ' + escape(persona.id) +
        ' / SIMULATION ROLLOUT</span><div class="placeholder-center"><span class="play-outline" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m7 4 13 8-13 8Z"/></svg></span><strong>Rollout video</strong><p>COMING SOON</p></div><span class="placeholder-corner" aria-hidden="true">PRB / ' + padded(example.id) + " / " + escape(persona.id) + '</span></div>';
    return '<div class="rollout-case">' + visual + '<div class="rollout-case-caption"><span class="persona-avatar"><span class="visually-hidden">Persona </span>' + escape(persona.id) +
      '</span><p>' + escape(persona.description) + '</p></div></div>';
  }

  function renderRolloutTabs() {
    const recorded = state.examples.filter((example) => example.recording);
    if (!recorded.length) return;
    // A tile per recorded pair: a real frame from persona A's recording (or the
    // initial scene) and the pair's label. Model recordings carry an on-screen
    // overlay, so their tiles use the scene.
    $(".rollout-tabs").innerHTML = recorded.map((example) => {
      const model = example.recording.kind === "model";
      const thumbnail = (model ? null : safeUrl(example.personas[0]?.videoPoster)) ?? safeUrl(example.poster);
      return '<button type="button" role="tab" id="example-tab-' + example.id + '" aria-controls="rollout-panel" aria-selected="false" tabindex="-1" data-example="' +
        example.id + '">' + (thumbnail ? '<img src="' + escape(thumbnail) + '" alt="" loading="lazy" width="160" height="100">' : "") +
        '<span>' + escape(example.tabLabel ?? example.shortTitle) + '</span></button>';
    }).join("");
    $(".rollout-tabs").classList.add("rollout-tiles");
    // Wide screens lay the tiles out in full rows of at most ten.
    const rows = Math.ceil(recorded.length / 10);
    $(".rollout-tabs").style.setProperty("--tile-columns", String(Math.ceil(recorded.length / rows)));
  }

  // One control drives every available persona on a shared simulation clock: a shorter
  // recording holds its last frame while the longer one finishes.
  function wireSync(example) {
    const bar = $("#rollout-sync");
    if (!bar) return;
    const videos = $$("video", $("#rollout-pair"));
    if (videos.length < 2) {
      bar.hidden = true;
      bar.innerHTML = "";
      return;
    }
    const recorded = example.personas.filter((persona) => safeUrl(persona.video));
    const duration = (video, index) => Number.isFinite(video.duration) && video.duration > 0
      ? video.duration : recorded[index].videoDurationSeconds || 0;
    const length = () => Math.max(0, ...videos.map(duration));
    const group = videos.length === 2 ? "both" : "all " + videos.length;
    const playLabel = '<span aria-hidden="true">▶</span> Play ' + group + ' together';
    const pauseLabel = '<span aria-hidden="true">❚❚</span> Pause ' + group;
    bar.hidden = false;
    bar.innerHTML = '<button type="button" class="sync-play">' + playLabel + '</button>' +
      '<button type="button" class="sync-skip" data-skip="-' + SKIP_SECONDS + '" aria-label="Back ' + SKIP_SECONDS + ' seconds">−' + SKIP_SECONDS + ' s</button>' +
      '<input class="sync-scrub" type="range" min="0" max="1000" step="1" value="0" aria-label="Position in ' + group + ' recordings">' +
      '<button type="button" class="sync-skip" data-skip="' + SKIP_SECONDS + '" aria-label="Forward ' + SKIP_SECONDS + ' seconds">+' + SKIP_SECONDS + ' s</button>' +
      '<span class="sync-time mono">0.0 / ' + length().toFixed(1) + ' s</span>' +
      '<div class="sync-speed" role="radiogroup" aria-label="Playback speed for ' + group + ' recordings">' +
      RATES.map((rate) => '<button type="button" role="radio" data-rate="' + rate + '" aria-checked="' + (rate === state.rate) + '">' + rate + '×</button>').join("") + '</div>';
    const play = $(".sync-play", bar);
    const scrub = $(".sync-scrub", bar);
    const time = $(".sync-time", bar);
    const clock = () => Math.max(0, ...videos.map((video) => video.currentTime || 0));
    const playing = () => videos.some((video) => !video.paused && !video.ended);
    const atEnd = (video, index) => video.ended || (duration(video, index) > 0 && video.currentTime >= duration(video, index) - 0.05);
    const finished = () => videos.every(atEnd);
    const start = (video) => {
      const started = video.play?.();
      if (started?.catch) started.catch(() => label());
    };
    const show = () => {
      const now = clock();
      scrub.value = String(length() ? Math.round(now / length() * 1000) : 0);
      time.textContent = now.toFixed(1) + " / " + length().toFixed(1) + " s";
    };
    const label = () => { play.innerHTML = playing() ? pauseLabel : playLabel; };
    const seek = (seconds, resume = playing()) => videos.forEach((video, index) => {
      const end = duration(video, index) || length();
      video.currentTime = Math.min(seconds, Math.max(0, end - 0.05));
      // A finished short clip stays on its last frame until the shared clock
      // returns to its range. Seeking backward during playback resumes it.
      if (resume) {
        if (atEnd(video, index)) video.pause();
        else start(video);
      }
    });
    const setRate = () => videos.forEach((video) => {
      video.defaultPlaybackRate = state.rate;
      video.playbackRate = state.rate;
    });
    setRate();
    for (const video of videos) {
      video.addEventListener("timeupdate", show);
      video.addEventListener("loadedmetadata", show);
      for (const type of ["play", "pause", "ended"]) video.addEventListener(type, label);
    }
    play.addEventListener("click", () => {
      if (playing()) {
        videos.forEach((video) => video.pause());
        label();
        return;
      }
      seek(finished() ? 0 : clock(), false);
      videos.forEach((video, index) => {
        if (atEnd(video, index)) video.pause();
        else start(video);
      });
      label();
    });
    const jump = (seconds) => {
      seek(Math.min(length(), Math.max(0, clock() + seconds)));
      show();
    };
    scrub.addEventListener("input", () => {
      seek(Number(scrub.value) / 1000 * length());
      show();
    });
    // Arrow keys on the bar move all available recordings by the skip step, not 1/1000 of the clip.
    scrub.addEventListener("keydown", (event) => {
      const step = { ArrowLeft: -SKIP_SECONDS, ArrowDown: -SKIP_SECONDS, ArrowRight: SKIP_SECONDS, ArrowUp: SKIP_SECONDS }[event.key];
      if (step === undefined) return;
      event.preventDefault();
      jump(step);
    });
    $$(".sync-skip", bar).forEach((button) => button.addEventListener("click", () => jump(Number(button.dataset.skip))));
    $(".sync-speed", bar).addEventListener("click", (event) => {
      const button = event.target.closest("[data-rate]");
      if (!button) return;
      state.rate = Number(button.dataset.rate);
      setRate();
      $$("[data-rate]", bar).forEach((item) => item.setAttribute("aria-checked", String(Number(item.dataset.rate) === state.rate)));
    });
  }

  function selectExample(id, focus = false) {
    const example = state.examples.find((item) => item.id === id);
    if (!example) return;
    $$("video", $("#rollout-pair")).forEach((video) => {
      if (!video.paused) video.pause();
    });
    state.activeExample = id;
    $$(".rollout-tabs [role=tab]").forEach((tab) => {
      const selected = Number(tab.dataset.example) === id;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected && focus) tab.focus();
    });
    $("#rollout-panel").setAttribute("aria-labelledby", "example-tab-" + id);
    $("#rollout-id").textContent = "Task " + padded(id) + " · " + example.shortTitle;
    $("#rollout-instruction").textContent = "“" + example.instruction + "”";
    const personas = example.personas;
    $("#rollout-pair").dataset.personaCount = String(personas.length);
    $("#rollout-pair").setAttribute("role", "group");
    $("#rollout-pair").setAttribute("aria-label", personas.length + " persona recordings");
    $("#rollout-pair").innerHTML = personas.map((persona, index) => rolloutCase(example, persona, index)).join("");
    const ready = personas.filter((persona) => safeUrl(persona.video)).length;
    wireSync(example);
    // Only missing videos need a status; complete recordings speak for themselves.
    $(".video-status").hidden = ready > 0 && ready === personas.length;
    const availability = ready === personas.length && ready > 0
      ? (ready === 2 ? "Paired videos available" : ready === 1 ? "Video available" : "All " + ready + " videos available")
      : ready ? ready + " of " + personas.length + " videos available" : "Videos coming soon";
    $(".video-status").innerHTML = "<i></i> " + availability;
    const recordingNote = $("#rollout-recording-note");
    if (recordingNote) {
      recordingNote.textContent = "";
      if (example.recording && ready) {
        const playback = example.recording.playback ?? "complete recorded episodes · 1× simulation playback; inference waits omitted.";
        recordingNote.textContent = playback.charAt(0).toUpperCase() + playback.slice(1);
        if (example.recording.recordedTaskId !== example.id) {
          recordingNote.textContent += " Recorded as Task " + example.recording.recordedTaskId + "; now Task " + example.id + ".";
        }
        const provenance = safeUrl(example.recording.provenance);
        if (provenance) {
          const details = document.createElement("a");
          details.href = provenance;
          details.textContent = "Recording details";
          recordingNote.append(" ", details);
        }
      }
    }
  }

  function setMenu(open) {
    $(".menu-toggle").setAttribute("aria-expanded", String(open));
    $(".menu-toggle").setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    $("#mobile-nav").hidden = !open;
  }

  function wireInteractions() {
    $(".filter-tabs").addEventListener("click", (event) => {
      const button = event.target.closest("[data-filter]");
      if (!button) return;
      state.category = button.dataset.filter;
      state.visible = PAGE_SIZE;
      renderTasks();
    });
    $("#task-search").addEventListener("input", (event) => {
      state.query = event.target.value;
      state.visible = PAGE_SIZE;
      renderTasks();
    });
    $("#show-more").addEventListener("click", () => {
      state.visible += 12;
      renderTasks();
    });
    $("#task-grid").addEventListener("click", (event) => {
      const button = event.target.closest("[data-task]");
      if (button) openTask(Number(button.dataset.task));
      if (event.target.closest("#clear-search")) {
        state.category = "All";
        state.query = "";
        state.visible = PAGE_SIZE;
        $("#task-search").value = "";
        renderTasks();
      }
    });
    $(".dialog-close").addEventListener("click", closeTask);
    $("#task-dialog").addEventListener("click", (event) => {
      if (event.target === $("#task-dialog")) {
        const bounds = $("#task-dialog").getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom) closeTask();
      }
    });
    $("#task-dialog").addEventListener("close", () => document.body.classList.remove("dialog-open"));
    $("#task-dialog").addEventListener("cancel", () => document.body.classList.remove("dialog-open"));
    $(".rollout-tabs").addEventListener("click", (event) => {
      const tab = event.target.closest("[data-example]");
      if (tab) selectExample(Number(tab.dataset.example));
    });
    $(".rollout-tabs").addEventListener("keydown", (event) => {
      const tabs = $$(".rollout-tabs [role=tab]");
      const current = tabs.findIndex((tab) => Number(tab.dataset.example) === state.activeExample);
      let next = current;
      if (event.key === "ArrowRight") next = (current + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (current + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectExample(Number(tabs[next].dataset.example), true);
    });
    $(".menu-toggle").addEventListener("click", () => setMenu($(".menu-toggle").getAttribute("aria-expanded") !== "true"));
    $$("#mobile-nav a").forEach((link) => link.addEventListener("click", () => setMenu(false)));
    document.addEventListener("keydown", (event) => {
      const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable;
      if (event.key === "/" && !typing && !$("#task-dialog").open) {
        event.preventDefault();
        $("#task-search").focus();
      }
      if (event.key === "Escape") {
        setMenu(false);
        if ($("#task-dialog").open) closeTask();
      }
    });

  }

  function renderLeaderboard(data) {
    if (data.schema !== "personarobotbench.website-leaderboard/1" || !Array.isArray(data.boards) || !data.boards.length) {
      throw new Error("Invalid leaderboard snapshot");
    }
    for (const board of data.boards) {
      if (!Array.isArray(board.rows) || !board.rows.length || !board.title || !board.metric) throw new Error("Invalid leaderboard board");
      for (const row of board.rows) {
        if (!row.policy || (row.scorePercent !== null && (typeof row.scorePercent !== "number" || !Number.isFinite(row.scorePercent) || row.scorePercent < 0 || row.scorePercent > 100))) {
          throw new Error("Invalid leaderboard score");
        }
      }
    }
    const description = $("#leaderboard-description");
    if (description) description.textContent = data.description || "Reported policy evaluations, with scoring criteria and coverage shown alongside each result.";
    $("#leaderboard-boards").innerHTML = data.boards.map((board, index) => {
      const rows = [...board.rows].sort((a, b) => (b.scorePercent ?? -1) - (a.scorePercent ?? -1));
      const maximum = Math.max(0, ...rows.filter((row) => row.scorePercent !== null).map((row) => row.scorePercent));
      const axisMax = Math.max(10, Math.ceil(maximum / 10) * 10);
      const tickStep = axisMax <= 10 ? 2 : axisMax <= 20 ? 5 : axisMax <= 50 ? 10 : 20;
      const ticks = [];
      for (let tick = 0; tick < axisMax; tick += tickStep) ticks.push(tick);
      ticks.push(axisMax);
      const titleId = "leaderboard-board-" + index;
      const captionId = titleId + "-metric";
      const tickMarkup = ticks.map((tick) => '<span style="left:' + (tick / axisMax * 100).toFixed(3) + '%">' + tick + '%</span>').join("");
      const chartRows = rows.map((row) => '<li class="leaderboard-chart-row' + (row.scorePercent === null ? ' is-pending' : '') + '" data-policy="' + escape(row.id) + '"><div class="leaderboard-chart-label"><span class="leaderboard-policy">' + escape(row.policy) +
        '</span><span class="leaderboard-variant">' + escape(row.variant) + '</span></div>' + (row.scorePercent === null
          ? '<span class="leaderboard-score leaderboard-unreported">Not reported</span>'
          : '<div class="leaderboard-bar-lane" aria-hidden="true"><span class="leaderboard-bar-fill" style="width:' + (row.scorePercent / axisMax * 100).toFixed(3) + '%"></span></div><span class="leaderboard-score">' + row.scorePercent.toFixed(1) + '<span>%</span></span>') + '</li>').join("");
      return '<section class="leaderboard-board" aria-labelledby="' + titleId + '"><div class="leaderboard-board-heading"><h3 id="' + titleId + '">' + escape(board.title) +
        '</h3><p>' + escape(board.description) + '</p></div><figure class="leaderboard-chart" aria-labelledby="' + captionId + '" data-axis-max="' + axisMax + '" style="--grid-step:' + (tickStep / axisMax * 100).toFixed(3) + '%"><figcaption id="' + captionId + '">' + escape(board.metric) +
        '<span class="visually-hidden">. Scale: 0 to ' + axisMax + ' percent.</span></figcaption><div class="leaderboard-chart-axis" aria-hidden="true"><div class="leaderboard-axis-track">' + tickMarkup + '</div></div><ol class="leaderboard-bars" role="list" aria-label="Policies ranked by ' + escape(board.metric) + '">' + chartRows +
        '</ol></figure></section>';
    }).join("");
    $("#leaderboard-status").textContent = data.updated ? "Results as of " + data.updated : "";
  }

  async function loadLeaderboard() {
    try {
      const response = await fetch("data/leaderboard.json", { cache: "no-cache" });
      if (!response.ok) throw new Error("Leaderboard unavailable");
      renderLeaderboard(await response.json());
      return true;
    } catch {
      $("#leaderboard-status").textContent = "The leaderboard is unavailable.";
      $("#leaderboard-boards").innerHTML = '<div class="empty-state"><p>Try again later.</p></div>';
      return false;
    }
  }

  async function start() {
    wireInteractions();
    try {
      const responses = await Promise.all([fetch("data/tasks.json", { cache: "no-cache" }), fetch("data/examples.json", { cache: "no-cache" })]);
      if (responses.some((response) => !response.ok)) throw new Error("Catalog unavailable");
      [state.tasks, state.examples] = await Promise.all(responses.map((response) => response.json()));
      if (state.tasks.length !== 100 || state.tasks.reduce((sum, task) => sum + task.personaCount, 0) !== 217) throw new Error("Catalog does not match the release");
      renderTasks();
      renderRolloutTabs();
      selectExample(state.examples.find((example) => example.recording)?.id ?? 1);
      return true;
    } catch {
      $("#task-count").textContent = "The interactive catalog is unavailable.";
      $("#task-grid").innerHTML = '<div class="empty-state"><p>The task catalog is temporarily unavailable. Refresh the page to try again.</p></div>';
      $("#rollout-pair").innerHTML = '<div class="empty-state">Task rollouts are temporarily unavailable. Refresh the page to try again.</div>';
      return false;
    }
  }

  window.prbReady = start();
  window.prbLeaderboardReady = loadLeaderboard();
})();

// Progressive enhancement: content remains visible without observer support.
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const revealObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('research-reveal');
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.section-heading, .concept-panel, .pipeline, .getting-started').forEach(element => revealObserver.observe(element));
}

(() => {
  const toggle = document.querySelector('#scene-toggle');
  if (!toggle) return;
  const reset = document.querySelector('#scene-reset');
  const viewport = document.querySelector('#scene-viewport');
  const host = document.querySelector('#scene-model-host');
  const status = document.querySelector('#scene-status');
  const initialOrbit = '25deg 70deg 4.1m';
  const initialTarget = '0m 0.85m 0m';
  let viewer, loading = false, ready = false, timeout;
  function showStatic() {
    viewport.classList.remove('is-3d');
    toggle.setAttribute('aria-pressed', 'false');
    toggle.querySelector('span').textContent = 'Explore in 3D';
    reset.disabled = true;
    if (viewer) viewer.setAttribute('aria-hidden', 'true');
  }
  function showModel() {
    viewport.classList.add('is-3d');
    toggle.setAttribute('aria-pressed', 'true');
    toggle.querySelector('span').textContent = 'Show image';
    viewer.removeAttribute('aria-hidden');
    reset.disabled = false;
    status.textContent = 'Drag to orbit · scroll / pinch to zoom';
  }
  function fail() {
    clearTimeout(timeout);
    loading = false;
    ready = false;
    toggle.disabled = false;
    showStatic();
    viewer?.remove();
    viewer = null;
    status.textContent = '3D unavailable. Image retained; click to retry.';
  }
  toggle.addEventListener('click', async () => {
    if (loading) return;
    if (ready) {
      if (viewport.classList.contains('is-3d')) {
        showStatic();
        status.textContent = 'Static scene preview';
      } else showModel();
      return;
    }
    loading = true;
    toggle.disabled = true;
    status.textContent = 'Loading 3D scene…';
    timeout = setTimeout(fail, 45000);
    try {
      if (!customElements.get('model-viewer')) {
        await new Promise((resolve, reject) => {
          let script = document.querySelector('#model-viewer-library');
          if (script) script.remove();
          script = document.createElement('script');
          script.id = 'model-viewer-library';
          script.type = 'module';
          script.src = 'assets/vendor/model-viewer.min.js';
          script.onload = resolve;
          script.onerror = reject;
          document.head.append(script);
        });
      }
      // The timeout may have restored the image during a slow library request.
      if (!loading) return;
      viewer = document.createElement('model-viewer');
      const attrs = {
        src: 'assets/models/shared-desk.glb',
        alt: 'Scene 001: original shared desk initial scene and Unitree G1. Drag or use arrow keys to orbit; scroll, pinch or Page Up and Page Down to zoom.',
        'camera-controls': '', 'touch-action': 'pan-y',
        'camera-orbit': initialOrbit, 'camera-target': initialTarget,
        'min-camera-orbit': 'auto 20deg 1.2m', 'max-camera-orbit': 'auto 85deg 9m',
        'field-of-view': '45deg', 'shadow-intensity': '0.85',
        'environment-image': 'assets/models/scene-environment.hdr', exposure: '1.15', 'tone-mapping': 'aces',
        'interaction-prompt': 'none', 'disable-pan': '', loading: 'eager',
        'aria-hidden': 'true'
      };
      Object.entries(attrs).forEach(([key, value]) => viewer.setAttribute(key, value));
      viewer.addEventListener('load', () => {
        clearTimeout(timeout);
        loading = false;
        ready = true;
        toggle.disabled = false;
        showModel();
      }, { once: true });
      viewer.addEventListener('error', fail, { once: true });
      host.append(viewer);
    } catch { fail(); }
  });
  reset.addEventListener('click', () => {
    if (!ready) return;
    viewer.setAttribute('camera-orbit', initialOrbit);
    viewer.setAttribute('camera-target', initialTarget);
    viewer.setAttribute('field-of-view', '45deg');
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) viewer.jumpCameraToGoal?.();
    status.textContent = 'View reset · drag to orbit · scroll to zoom';
  });
})();
