/* PersonaRobotBench: no framework, analytics, secrets, or model calls. */
(() => {
  "use strict";

  const FEATURED = [18, 51, 68, 87, 32, 91];
  const PAGE_SIZE = 6;
  const state = { tasks: [], examples: [], category: "All", query: "", visible: PAGE_SIZE, activeExample: 18 };
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
  const posterFor = (task) => state.examples.find((item) => item.id === task.id)?.poster
    ?? ({ 1: "assets/hero-scene.webp", 13: "assets/scene-bookshelf.webp", 82: "assets/scene-workbench.webp" }[task.id] ?? null);
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
      ? '<img src="' + escape(poster) + '" alt="Authored simulation scene for ' + escape(titleFor(task)) + '" loading="lazy" width="960" height="600">'
      : schematic(task.id);
    const dots = task.personaIds.map((id, index) => '<span class="persona-pill ' + (index % 2 ? "persona-b-color" : "persona-a-color") + '">' + escape(id) + '</span>').join("");
    return '<article class="task-card"><button class="task-card-button" type="button" data-task="' + task.id + '" aria-label="View Task ' + task.id + ': ' + escape(titleFor(task)) + ', ' + task.personaCount + ' persona cases"><div class="task-image">' + figure +
      '<span class="task-number">TASK ' + padded(task.id) + '</span><span class="task-preview-label">' + (poster ? "STATIC SCENE PREVIEW" : "TASK SPECIFICATION") +
      '</span></div><div class="task-card-body"><div class="task-card-heading"><h3>' + escape(titleFor(task)) + '</h3><span class="task-card-arrow" aria-hidden="true">↗</span></div><p>“' + escape(task.instruction) +
      '”</p><div class="task-card-footer"><span class="category">' + escape(task.category) + '</span><span class="persona-dots" aria-label="' + task.personaCount + ' persona cases">' + dots + '<span>' +
      task.personaCount + ' cases</span></span></div></div></button></article>';
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
      ? '<img src="' + escape(poster) + '" alt="Static simulation scene for ' + escape(titleFor(task)) + '" width="960" height="600">'
      : schematic(task.id)) + '</div><div class="dialog-body"><span class="mono small-label">TASK ' + padded(task.id) + " / " + escape(task.category.toUpperCase()) +
      '</span><h2 id="task-dialog-title">' + escape(titleFor(task)) + '</h2><p class="dialog-instruction">“' + escape(task.instruction) +
      '”</p><div class="dialog-personas">' + task.personas.map((persona) => '<div class="dialog-persona"><span class="mono small-label">PERSONA ' + escape(persona.id) +
        '</span><p>' + escape(persona.description) + '</p></div>').join("") +
      '</div><p class="dialog-note">These are authored, task-local persona cases. The scene image is a reference preview; it does not establish a completed policy rollout.' +
      ([20, 21].includes(task.id) ? " This imported task has documented differences and incomplete validation; consult its package notes." : "") +
      '</p><a class="button button-dark" href="' + escape(safeUrl(task.sourceUrl) ?? "#tasks") + '" target="_blank" rel="noopener noreferrer">View task package <span aria-hidden="true">↗</span></a></div>';
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
    return '<div class="rollout-case">' + visual + '<div class="rollout-case-caption"><span class="persona-avatar">' + escape(persona.id) +
      '</span><div><span class="mono small-label">PERSONA ' + escape(persona.id) + '</span><p>' + escape(persona.description) + '</p></div></div></div>';
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
    $("#rollout-id").textContent = "TASK " + padded(id) + " · " + example.shortTitle.toUpperCase();
    $("#rollout-instruction").textContent = "“" + example.instruction + "”";
    const personas = example.personas.slice(0, 2);
    $("#rollout-pair").innerHTML = personas.map((persona, index) => rolloutCase(example, persona, index)).join("");
    const ready = personas.filter((persona) => safeUrl(persona.video)).length;
    $(".video-status").innerHTML = "<i></i> " + (ready === 2 ? "Paired videos available" : ready === 1 ? "1 of 2 videos available" : "Videos coming soon");
    const recordingNote = $("#rollout-recording-note");
    if (recordingNote) {
      recordingNote.textContent = "";
      if (example.recording && ready) {
        const label = example.recording.model === "gpt-6-astra" ? "Astra" : example.recording.model;
        recordingNote.textContent = label + " · complete recorded episodes · 1× simulation playback; inference waits omitted.";
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
    $("#copy-code").addEventListener("click", async () => {
      const text = $("#quickstart-code").textContent.trim();
      try {
        if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(text);
        $("#copy-status").textContent = "Commands copied.";
        $("#copy-code").innerHTML = 'Copied <span aria-hidden="true">✓</span>';
      } catch {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents($("#quickstart-code"));
        selection.removeAllRanges();
        selection.addRange(range);
        $("#copy-status").textContent = "Commands selected. Press Ctrl+C or ⌘C to copy.";
      }
    });
  }

  async function start() {
    wireInteractions();
    try {
      const responses = await Promise.all([fetch("data/tasks.json"), fetch("data/examples.json")]);
      if (responses.some((response) => !response.ok)) throw new Error("Catalog unavailable");
      [state.tasks, state.examples] = await Promise.all(responses.map((response) => response.json()));
      if (state.tasks.length !== 100 || state.tasks.reduce((sum, task) => sum + task.personaCount, 0) !== 217) throw new Error("Catalog does not match the release");
      renderTasks();
      selectExample(18);
      return true;
    } catch {
      $("#task-count").textContent = "The interactive catalog is unavailable.";
      $("#task-grid").innerHTML = '<div class="empty-state"><p>Please serve this site over HTTP, or browse the public task catalog on GitHub.</p><a class="text-link" href="https://github.com/HHD000EXE/PersonaRobotBench-website/blob/website/data/tasks.json" target="_blank" rel="noopener noreferrer">Browse the public task catalog ↗</a></div>';
      $("#rollout-pair").innerHTML = '<div class="empty-state">Recorded rollouts are unavailable. <a href="https://github.com/HHD000EXE/PersonaRobotBench-website/tree/website/assets/rollouts" target="_blank" rel="noopener noreferrer">View or download the videos on GitHub.</a></div>';
      return false;
    }
  }

  window.prbReady = start();
})();
