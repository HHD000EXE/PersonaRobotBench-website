/* PersonaRobotBench: no framework, analytics, secrets, or model calls. */
(() => {
  "use strict";

  const FEATURED = [18, 51, 68, 87, 32, 91];
  const PAGE_SIZE = 6;
  const RATES = [1, 2, 4, 8];
  const SKIP_SECONDS = 5;
  const state = { tasks: [], examples: [], category: "All", query: "", visible: PAGE_SIZE, rate: 1,
    astraGroups: [], geminiGroups: [], geminiAvailable: false, rolloutGroups: [], activeGroup: null };
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

  // One gallery, grouped by the policy that produced the recordings. Astra and
  // scripted examples come from data/examples.json; Gemini 4 replays come from
  // data/gemini4-rollouts.json. Tiles stay unlabelled; the panel names the model.
  const RECORDING_KINDS = { model: "model rollout", scripted: "scripted reference" };

  function astraGroup(example) {
    const model = example.recording.kind === "model";
    return {
      key: "astra-" + example.id,
      kind: "astra",
      taskId: example.id,
      title: example.title,
      shortTitle: example.shortTitle,
      instruction: example.instruction,
      tabLabel: example.tabLabel ?? example.shortTitle,
      thumbnail: (model ? null : safeUrl(example.personas[0]?.videoPoster)) ?? safeUrl(example.poster),
      poster: example.poster,
      modelLine: (example.recording.label || "Astra") + " · " + (RECORDING_KINDS[example.recording.kind] || "recorded episode"),
      recording: example.recording,
      personas: example.personas.map((persona) => ({
        id: persona.id,
        description: persona.description,
        video: persona.video,
        poster: persona.videoPoster || example.poster,
        duration: persona.videoDurationSeconds || 0
      }))
    };
  }

  function geminiGroup(items) {
    const first = items[0];
    return {
      key: "gemini4-" + first.taskId,
      kind: "gemini4",
      taskId: first.taskId,
      title: first.title,
      shortTitle: first.taskKey,
      instruction: first.instruction,
      tabLabel: first.title,
      thumbnail: safeUrl(first.poster),
      poster: null,
      modelLine: first.model + " · " + (first.reasoningEffort || "medium") + " reasoning · recorded replay",
      recording: null,
      personas: items.map((item) => ({
        id: item.persona,
        description: item.personaDescription,
        video: item.video,
        poster: item.poster,
        duration: item.durationSeconds || 0,
        outcome: item.outcome,
        seeds: Array.isArray(item.strictSuccessSeeds) ? item.strictSuccessSeeds : [],
        captions: Array.isArray(item.captions) ? item.captions : []
      }))
    };
  }

  function groupTabId(group) {
    return (group.kind === "gemini4" ? "gemini4-tab-" : "example-tab-") + group.taskId;
  }

  function personaExtras(persona) {
    const badge = persona.outcome
      ? '<span class="gemini4-badge ' + (persona.outcome === "SUCCESS" ? "is-success" : "is-failed") + '">' + (persona.outcome === "SUCCESS" ? "SUCCESS" : "FAILED") + "</span>"
      : "";
    let body = "";
    if (persona.seeds) body += '<p class="rollout-seeds mono">Strict successes for this persona: ' + persona.seeds.length + " / 10 seeds</p>";
    const captions = (persona.captions || []).map((call) =>
      '<div class="gemini4-caption"><span class="mono small-label">Skill call ' + escape(call.skillCall) + (call.startSeconds != null ? " · " + escape(Number(call.startSeconds).toFixed(1)) + " s" : "") + '</span>' +
      (call.full_call ? '<pre class="gemini4-call">' + escape(call.full_call) + '</pre>' : "") +
      (call.full_rationale ? '<p class="gemini4-rationale">' + escape(call.full_rationale) + "</p>" : "") + "</div>").join("");
    if (captions) body += '<div class="gemini4-captions"><p class="gemini4-captions-title">Full text shortened in the video panel</p>' + captions + "</div>";
    return { badge, body };
  }

  function rolloutCase(group, persona) {
    const source = safeUrl(persona.video);
    const poster = safeUrl(persona.poster) ?? safeUrl(group.poster);
    const extension = source ? new URL(source).pathname.toLowerCase().split(".").pop() : "";
    const mime = ({ mp4: "video/mp4", webm: "video/webm" })[extension];
    const extras = personaExtras(persona);
    const visual = source
      ? '<video class="rollout-video" controls playsinline preload="metadata" poster="' + escape(poster ?? "") + '" aria-label="Task ' + group.taskId + " persona " + escape(persona.id) + ' recorded episode"><source src="' + escape(source) + '"' + (mime ? ' type="' + mime + '"' : '') + '>Your browser does not support embedded video. <a href="' + escape(source) + '">Download the recording</a>.</video>'
      : '<div class="video-placeholder" role="img" aria-label="Video placeholder for Task ' + group.taskId + " persona " + escape(persona.id) +
        '"><img src="' + escape(group.poster ?? "") + '" alt="" loading="lazy" width="960" height="600"><span class="video-placeholder-label">PERSONA ' + escape(persona.id) +
        ' / RECORDED EPISODE</span><div class="placeholder-center"><span class="play-outline" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="m7 4 13 8-13 8Z"/></svg></span><strong>Rollout video</strong><p>COMING SOON</p></div><span class="placeholder-corner" aria-hidden="true">PRB / ' + padded(group.taskId) + " / " + escape(persona.id) + '</span></div>';
    return '<div class="rollout-case">' + visual +
      '<div class="rollout-case-caption"><span class="persona-avatar"><span class="visually-hidden">Persona </span>' + escape(persona.id) + "</span>" +
      '<div class="rollout-case-text"><p>' + escape(persona.description) + "</p>" + extras.body + "</div>" + extras.badge + "</div></div>";
  }

  function rolloutTile(group) {
    return '<button type="button" role="tab" id="' + escape(groupTabId(group)) + '" aria-controls="rollout-panel" aria-selected="false" tabindex="-1" data-group="' + escape(group.key) + '" data-example="' + escape(group.taskId) + '">' +
      (group.thumbnail ? '<img src="' + escape(group.thumbnail) + '" alt="" loading="lazy" width="160" height="100">' : "") +
      '<span>' + escape(group.tabLabel) + '</span></button>';
  }

  function rolloutGroupSection(id, title, note, groups) {
    if (!groups.length) return "";
    // Wide screens lay each group out in full rows of at most ten tiles.
    const rows = Math.ceil(groups.length / 10);
    return '<section class="rollout-group" aria-labelledby="rollout-group-' + id + '">' +
      '<header class="rollout-group-head"><h3 id="rollout-group-' + id + '">' + escape(title) + '</h3><p>' + escape(note) + '</p></header>' +
      '<div class="rollout-tabs rollout-tiles" role="tablist" aria-label="' + escape(title) + ' recordings" style="--tile-columns:' +
      Math.ceil(groups.length / rows) + '">' + groups.map(rolloutTile).join("") + "</div></section>";
  }

  function renderRolloutGroups() {
    const astra = state.rolloutGroups.filter((group) => group.kind === "astra");
    const gemini = state.rolloutGroups.filter((group) => group.kind === "gemini4");
    const geminiNote = state.geminiAvailable
      ? "Recorded Gemini 4 (medium reasoning) episodes from the final merged evaluation run, one tile per task."
      : "Gemini 4 replays are unavailable right now. The Astra and scripted recordings remain available.";
    $("#rollout-groups").innerHTML =
      rolloutGroupSection("astra", "Astra and scripted references", "Selected development demonstrations and scripted reference controllers on benchmark tasks.", astra) +
      (state.geminiAvailable
        ? rolloutGroupSection("gemini4", "Gemini 4", geminiNote, gemini)
        : '<p id="rollout-gemini-status" class="rollout-group-empty">' + escape(geminiNote) + "</p>");
  }

  // One control drives every available recording on a shared simulation clock: a
  // shorter clip holds its last frame while the longer one finishes.
  function wireSyncVideos(videos, bar, durations = []) {
    if (!bar) return;
    if (videos.length < 2) {
      bar.hidden = true;
      bar.innerHTML = "";
      return;
    }
    const duration = (video, index) => Number.isFinite(video.duration) && video.duration > 0
      ? video.duration : (durations[index] || 0);
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

  function wireSync(group) {
    wireSyncVideos($$("video", $("#rollout-pair")), $("#rollout-sync"), group.personas.map((persona) => persona.duration || 0));
  }

  function recordingNoteFor(group) {
    if (group.kind === "gemini4") {
      return "Recorded Gemini 4 episode from the final merged evaluation run (medium reasoning, seeds 100–109). SUCCESS or FAILED is the native strict-success outcome of the shown seed; these replays are separate from the leaderboard success rate.";
    }
    const recording = group.recording;
    if (!recording) return "";
    const playback = recording.playback ?? "complete recorded episodes · 1× simulation playback; inference waits omitted.";
    let note = playback.charAt(0).toUpperCase() + playback.slice(1);
    if (recording.recordedTaskId !== group.taskId) {
      note += " Recorded as Task " + recording.recordedTaskId + "; now Task " + group.taskId + ".";
    }
    return note;
  }

  function selectGroup(key, focus = false) {
    const group = state.rolloutGroups.find((item) => item.key === key);
    if (!group) return;
    $$("video", $("#rollout-pair")).forEach((video) => {
      if (!video.paused) video.pause();
    });
    state.activeGroup = key;
    $$("#rollout-groups [role=tab]").forEach((tab) => {
      const selected = tab.dataset.group === key;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
      if (selected && focus) tab.focus();
    });
    $("#rollout-panel").setAttribute("aria-labelledby", groupTabId(group));
    $("#rollout-id").textContent = "Task " + padded(group.taskId) + " · " + (group.shortTitle || group.title);
    $("#rollout-instruction").textContent = "“" + group.instruction + "”";
    const model = $("#rollout-model");
    if (model) model.textContent = group.modelLine;
    const personas = group.personas;
    $("#rollout-pair").dataset.personaCount = String(personas.length);
    $("#rollout-pair").setAttribute("role", "group");
    $("#rollout-pair").setAttribute("aria-label", personas.length + " persona recordings");
    $("#rollout-pair").innerHTML = personas.map((persona) => rolloutCase(group, persona)).join("");
    const ready = personas.filter((persona) => safeUrl(persona.video)).length;
    wireSync(group);
    // Only missing videos need a status; complete recordings speak for themselves.
    $(".video-status").hidden = ready > 0 && ready === personas.length;
    const availability = ready === personas.length && ready > 0
      ? (ready === 2 ? "Paired videos available" : ready === 1 ? "Video available" : "All " + ready + " videos available")
      : ready ? ready + " of " + personas.length + " videos available" : "Videos coming soon";
    $(".video-status").innerHTML = "<i></i> " + availability;
    const recordingNote = $("#rollout-recording-note");
    if (recordingNote) {
      recordingNote.textContent = "";
      if (ready) {
        recordingNote.textContent = recordingNoteFor(group);
        const provenance = safeUrl(group.recording?.provenance);
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
    $("#rollout-groups").addEventListener("click", (event) => {
      const tab = event.target.closest("[data-group]");
      if (tab) selectGroup(tab.dataset.group);
    });
    $("#rollout-groups").addEventListener("keydown", (event) => {
      const list = event.target.closest('[role="tablist"]');
      if (!list) return;
      const tabs = $$('[role="tab"]', list);
      const index = tabs.indexOf(event.target.closest('[role="tab"]'));
      if (index < 0) return;
      let next = index;
      if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
      else if (event.key === "ArrowLeft") next = (index + tabs.length - 1) % tabs.length;
      else if (event.key === "Home") next = 0;
      else if (event.key === "End") next = tabs.length - 1;
      else return;
      event.preventDefault();
      selectGroup(tabs[next].dataset.group, true);
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
      const unit = board.unit || "%";
      const ticks = [];
      for (let tick = 0; tick < axisMax; tick += tickStep) ticks.push(tick);
      ticks.push(axisMax);
      const titleId = "leaderboard-board-" + index;
      const captionId = titleId + "-metric";
      const tickMarkup = ticks.map((tick) => '<span style="left:' + (tick / axisMax * 100).toFixed(3) + '%">' + tick + escape(unit) + '</span>').join("");
      const chartRows = rows.map((row) => '<li class="leaderboard-chart-row' + (row.scorePercent === null ? ' is-pending' : '') + '" data-policy="' + escape(row.id) + '"><div class="leaderboard-chart-label"><span class="leaderboard-policy">' + escape(row.policy) +
        '</span><span class="leaderboard-variant">' + escape(row.variant) + '</span></div>' + (row.scorePercent === null
          ? '<span class="leaderboard-score leaderboard-unreported">Not reported</span>'
          : '<div class="leaderboard-bar-lane" aria-hidden="true"><span class="leaderboard-bar-fill" style="width:' + (row.scorePercent / axisMax * 100).toFixed(3) + '%"></span></div><span class="leaderboard-score">' + row.scorePercent.toFixed(1) + '<span>' + escape(unit) + '</span></span>') + '</li>').join("");
      return '<section class="leaderboard-board" aria-labelledby="' + titleId + '"><div class="leaderboard-board-heading"><h3 id="' + titleId + '">' + escape(board.title) +
        '</h3><p>' + escape(board.description) + '</p></div><figure class="leaderboard-chart" aria-labelledby="' + captionId + '" data-axis-max="' + axisMax + '" style="--grid-step:' + (tickStep / axisMax * 100).toFixed(3) + '%"><figcaption id="' + captionId + '">' + escape(board.metric) +
        '<span class="visually-hidden">. Scale: 0 to ' + axisMax + (unit === "%" ? " percent" : " " + escape(unit)) + '.</span></figcaption><div class="leaderboard-chart-axis" aria-hidden="true"><div class="leaderboard-axis-track">' + tickMarkup + '</div></div><ol class="leaderboard-bars" role="list" aria-label="Policies ranked by ' + escape(board.metric) + '">' + chartRows +
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

  // Gemini 4 replays join the same gallery as their own group.
  function gemini4GroupsFrom(data) {
    if (!data || data.schema !== "personarobotbench.website-gemini4-rollouts/1" || !Array.isArray(data.entries)) throw new Error("Unknown gallery data");
    const groups = new Map();
    for (const item of data.entries) {
      if (!groups.has(item.taskId)) groups.set(item.taskId, []);
      groups.get(item.taskId).push(item);
    }
    return [...groups.values()].map(geminiGroup);
  }

  async function loadGemini4() {
    try {
      const response = await fetch("data/gemini4-rollouts.json", { cache: "no-cache" });
      if (!response.ok) throw new Error("Gallery unavailable");
      state.geminiGroups = gemini4GroupsFrom(await response.json());
      state.geminiAvailable = true;
      return true;
    } catch {
      state.geminiGroups = [];
      state.geminiAvailable = false;
      return false;
    }
  }

  // Task 1 overview: choose a persona and watch that user's recorded rollout.
  function wireOverviewPersona() {
    const group = $("#overview-persona-switch");
    const player = $("#overview-player");
    const video = $("#overview-video");
    const viewport = $("#scene-viewport");
    const note = $("#overview-rollout-note");
    const controls = $(".scene-view-buttons");
    const status = $("#scene-status");
    const example = state.examples.find((item) => item.id === 1);
    if (!group || !player || !video || !viewport || !example) return;
    const personas = new Map(example.personas.map((persona) => [persona.id, persona]));
    const buttons = $$("[data-overview-view]", group);
    const show = (view) => {
      buttons.forEach((button) => button.setAttribute("aria-pressed", String(button.dataset.overviewView === view)));
      const persona = personas.get(view);
      const source = persona ? safeUrl(persona.video) : null;
      if (view === "scene" || !source) {
        if (!video.paused) video.pause();
        video.removeAttribute("src");
        player.hidden = true;
        viewport.hidden = false;
        if (controls) controls.hidden = false;
        if (status) status.textContent = viewport.classList.contains("is-3d") ? "Drag to orbit · scroll / pinch to zoom" : "Static scene preview";
        if (note) note.textContent = view === "scene"
          ? "Static initial scene. Choose a persona to watch that user's recorded Task 1 rollout."
          : "That persona recording is not available yet.";
        return;
      }
      video.pause();
      video.src = source;
      const poster = safeUrl(persona.videoPoster);
      if (poster) video.poster = poster; else video.removeAttribute("poster");
      video.setAttribute("aria-label", "Task 1 persona " + view + " recorded rollout");
      player.hidden = false;
      viewport.hidden = true;
      if (controls) controls.hidden = true;
      if (status) status.textContent = "Recorded rollout · Task 1 · Persona " + view;
      if (note) note.textContent = "Persona " + view + " — " + (persona.description || "");
    };
    group.addEventListener("click", (event) => {
      const button = event.target.closest("[data-overview-view]");
      if (button) show(button.dataset.overviewView);
    });
    show("scene");
  }

  async function start() {
    wireInteractions();
    try {
      const responses = await Promise.all([fetch("data/tasks.json", { cache: "no-cache" }), fetch("data/examples.json", { cache: "no-cache" })]);
      if (responses.some((response) => !response.ok)) throw new Error("Catalog unavailable");
      [state.tasks, state.examples] = await Promise.all(responses.map((response) => response.json()));
      if (state.tasks.length !== 100 || state.tasks.reduce((sum, task) => sum + task.personaCount, 0) !== 217) throw new Error("Catalog does not match the release");
      renderTasks();
      state.astraGroups = state.examples.filter((example) => example.recording).map(astraGroup);
      state.rolloutGroups = [...state.astraGroups];
      renderRolloutGroups();
      if (state.rolloutGroups.length) selectGroup(state.rolloutGroups[0].key);
      wireOverviewPersona();
      return true;
    } catch {
      $("#task-count").textContent = "The interactive catalog is unavailable.";
      $("#task-grid").innerHTML = '<div class="empty-state"><p>The task catalog is temporarily unavailable. Refresh the page to try again.</p></div>';
      $("#rollout-pair").innerHTML = '<div class="empty-state">Task rollouts are temporarily unavailable. Refresh the page to try again.</div>';
      return false;
    }
  }

  async function loadGallery() {
    const catalog = await start();
    if (!catalog) return { catalog: false, gemini: false };
    const gemini = await loadGemini4();
    state.rolloutGroups = [...state.astraGroups, ...state.geminiGroups];
    renderRolloutGroups();
    const active = state.rolloutGroups.find((group) => group.key === state.activeGroup) || state.rolloutGroups[0];
    if (active) selectGroup(active.key);
    return { catalog: true, gemini };
  }

  const gallery = loadGallery();
  window.prbReady = gallery.then((result) => result.catalog);
  window.prbLeaderboardReady = loadLeaderboard();
  window.prbGemini4Ready = gallery.then((result) => result.gemini);
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

// V2D robot videos: a tile per source clip swaps the single player's content.
(() => {
  const tiles = document.querySelector('#v2d-demos .v2d-tiles');
  const player = document.querySelector('#v2d-player');
  if (!tiles || !player) return;
  const buttons = [...tiles.querySelectorAll('[data-v2d-demo]')];
  const select = (button, focus = false) => {
    const template = document.getElementById('v2d-demo-' + button.dataset.v2dDemo);
    if (!template || button.getAttribute('aria-selected') === 'true') {
      if (focus) button.focus();
      return;
    }
    player.querySelectorAll('video').forEach((video) => video.pause());
    // Import into this document so the media elements load their posters normally.
    player.replaceChildren(document.importNode(template.content, true));
    player.setAttribute('aria-labelledby', button.id);
    buttons.forEach((other) => {
      const active = other === button;
      other.setAttribute('aria-selected', String(active));
      other.tabIndex = active ? 0 : -1;
    });
    if (focus) button.focus();
  };
  tiles.addEventListener('click', (event) => {
    const button = event.target.closest('[data-v2d-demo]');
    if (button) select(button);
  });
  // Pairs: one button starts both recordings from the beginning, or pauses both.
  player.addEventListener('click', (event) => {
    const control = event.target.closest('.v2d-play-both');
    if (!control) return;
    const videos = [...player.querySelectorAll('video')];
    const playing = videos.some((video) => !video.paused && !video.ended);
    if (playing) {
      videos.forEach((video) => video.pause());
      control.innerHTML = '<span aria-hidden="true">▶</span> Play both together';
      return;
    }
    videos.forEach((video) => {
      video.preload = 'auto';
      video.currentTime = 0;
      video.play()?.catch?.(() => {});
    });
    control.innerHTML = '<span aria-hidden="true">❚❚</span> Pause both';
  });
  tiles.addEventListener('keydown', (event) => {
    const current = buttons.findIndex((button) => button.getAttribute('aria-selected') === 'true');
    const next = { ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: buttons.length - 1 }[event.key];
    if (next === undefined) return;
    event.preventDefault();
    select(buttons[(next + buttons.length) % buttons.length], true);
  });
})();
