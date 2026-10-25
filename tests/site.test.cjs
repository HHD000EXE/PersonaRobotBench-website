/* Offline DOM behavior checks. jsdom is a development-only dependency. */
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const app = fs.readFileSync(path.join(root, 'app.js'), 'utf8');
const tasks = JSON.parse(fs.readFileSync(path.join(root, 'data/tasks.json'), 'utf8'));
const shippedExamples = JSON.parse(fs.readFileSync(path.join(root, 'data/examples.json'), 'utf8'));
const shippedLeaderboard = JSON.parse(fs.readFileSync(path.join(root, 'data/leaderboard.json'), 'utf8'));
const examples = structuredClone(shippedExamples);
// Placeholder behavior must remain testable after contributors add real videos.
// These fixtures never modify the published examples file.
for (const example of examples) {
  for (const persona of example.personas) persona.video = null;
}

// Synthetic scores exercise display behavior independently of paper results.
const leaderboardFixture = {
  schema: 'personarobotbench.website-leaderboard/1', updated: '2026-10-25',
  description: 'Reported evaluations with explicit criteria.',
  boards: [{ id: 'strict', title: 'Personalized success', metric: 'Success rate',
    description: 'Goal, process and fidelity must pass.', notes: ['Different trial budgets are shown per policy.'],
    rows: [
      { id: 'first', policy: 'Policy A', variant: 'API', scorePercent: 12.3, coverage: '100 tasks · 217 cases', protocol: '10 trials / persona', notes: 'Source-derived score.' },
      { id: 'pending', policy: 'Policy pending', variant: 'API', scorePercent: null, coverage: 'Not reported', protocol: 'Not reported', notes: '' },
      { id: 'second', policy: 'Policy B', variant: 'CLI', scorePercent: 77.7, coverage: '100 tasks · 217 cases', protocol: '3 trials / persona', notes: 'Author-reported score.' }
    ]
  }, { id: 'goal', title: 'Goal-only study', metric: 'Goal completion',
    description: 'Goal-only outcome; separate from personalized success.', notes: [],
    rows: [{ id: 'goal-policy', policy: 'Policy A', variant: 'API', scorePercent: 95.0, coverage: '217 cases', protocol: '3 trials / persona', notes: '' }]
  }]
};

async function boot(options = {}) {
  const dom = new JSDOM(html, { url: options.url || 'https://benchmark.test/', runScripts: 'outside-only', pretendToBeVisual: true });
  const { window } = dom;
  const pausedVideos = [];
  window.HTMLMediaElement.prototype.pause = function () { pausedVideos.push(this); };
  const requests = [];
  window.fetch = async (url) => {
    requests.push(new URL(url, window.location.href).href);
    const isLeaderboard = url.includes('leaderboard.json');
    const data = isLeaderboard ? (options.leaderboard || leaderboardFixture)
      : url.includes('tasks.json') ? (options.tasks || tasks) : (options.examples || examples);
    return { ok: !(options.fetchError || (isLeaderboard ? options.leaderboardError : options.catalogError)), json: async () => structuredClone(data) };
  };
  window.eval(app);
  const ready = await window.prbReady;
  const leaderboardReady = await window.prbLeaderboardReady;
  return { dom, window, requests, pausedVideos, leaderboardReady, document: window.document, ready, $: (selector) => window.document.querySelector(selector), $$: (selector) => [...window.document.querySelectorAll(selector)] };
}

function input(context, value) {
  context.$('#task-search').value = value;
  context.$('#task-search').dispatchEvent(new context.window.Event('input', { bubbles: true }));
}

test('release catalog boots with six featured cards and correct total', async () => {
  const ctx = await boot();
  assert.equal(ctx.ready, true);
  assert.equal(tasks.length, 100);
  assert.equal(tasks.reduce((sum, task) => sum + task.personaCount, 0), 217);
  assert.equal(ctx.$$('.task-card').length, 6);
  assert.equal(ctx.$('#task-count').textContent, 'Showing 6 of 100 tasks');
  assert.deepEqual(ctx.$$('[data-task]').map((button) => Number(button.dataset.task)), [18, 51, 68, 87, 32, 91]);
  ctx.window.close();
});

test('all six category filters return only matching tasks', async () => {
  const ctx = await boot();
  for (const category of new Set(tasks.map((task) => task.category))) {
    ctx.$$('[data-filter]').find((button) => button.dataset.filter === category).click();
    const expected = tasks.filter((task) => task.category === category);
    assert.equal(ctx.$$('.task-card').length, Math.min(6, expected.length));
    for (const card of ctx.$$('[data-task]')) assert.equal(tasks.find((task) => task.id === Number(card.dataset.task)).category, category);
    assert.equal(ctx.$$('[aria-pressed="true"]').length, 1);
  }
  ctx.window.close();
});

test('numeric, prefixed, title and persona-text search work', async () => {
  const ctx = await boot();
  for (const query of ['18', '018', 'Task #18', 'sparkling water']) {
    input(ctx, query);
    assert.ok(ctx.$$('[data-task]').some((button) => button.dataset.task === '18'));
    if (/18/.test(query)) assert.equal(ctx.$$('.task-card').length, 1);
  }
  input(ctx, 'stamp press');
  assert.ok(ctx.$$('[data-task]').some((button) => button.dataset.task === '51'));
  ctx.window.close();
});

test('empty state clears both search and category', async () => {
  const ctx = await boot();
  ctx.$$('[data-filter]').find((button) => button.dataset.filter === 'Workspace').click();
  input(ctx, 'does-not-exist-999999');
  assert.equal(ctx.$('#task-count').textContent, '0 tasks found');
  assert.equal(ctx.$('#show-more').hidden, true);
  ctx.$('#clear-search').click();
  assert.equal(ctx.$('#task-search').value, '');
  assert.equal(ctx.$('#task-count').textContent, 'Showing 6 of 100 tasks');
  assert.equal(ctx.$('[data-filter="All"]').getAttribute('aria-pressed'), 'true');
  ctx.window.close();
});

test('show more reaches every task then hides its button', async () => {
  const ctx = await boot();
  ctx.$('#show-more').click();
  assert.equal(ctx.$$('.task-card').length, 18);
  while (!ctx.$('#show-more').hidden) ctx.$('#show-more').click();
  assert.equal(ctx.$$('.task-card').length, 100);
  assert.equal(new Set(ctx.$$('[data-task]').map((button) => button.dataset.task)).size, 100);
  ctx.window.close();
});

test('all 100 task cards and dialogs use their own initial scene preview', async () => {
  const ctx = await boot();
  while (!ctx.$('#show-more').hidden) ctx.$('#show-more').click();
  assert.equal(ctx.$$('.task-schematic').length, 0);
  const imagePaths = new Set();
  for (const button of ctx.$$('[data-task]')) {
    const task = tasks.find((item) => item.id === Number(button.dataset.task));
    assert.ok(task.preview?.image, 'Task ' + task.id + ' lacks a preview');
    assert.ok(task.preview.alt, 'Task ' + task.id + ' lacks scene alt text');
    assert.match(task.preview.image, /^assets\/task-scenes\/task-\d{3}\.webp$/);
    assert.equal(button.querySelector('img').src, 'https://benchmark.test/' + task.preview.image);
    assert.equal(button.querySelector('img').alt, task.preview.alt);
    assert.equal(button.querySelector('.task-preview-label').textContent, 'INITIAL SCENE');
    imagePaths.add(task.preview.image);
    button.click();
    assert.equal(ctx.$('.dialog-cover img').src, 'https://benchmark.test/' + task.preview.image);
    assert.equal(ctx.$('.dialog-cover img').alt, task.preview.alt);
    ctx.$('.dialog-close').click();
  }
  assert.equal(imagePaths.size, 100);
  ctx.window.close();
});

test('task dialog displays every authored persona and closes with Escape', async () => {
  const ctx = await boot();
  input(ctx, '32');
  ctx.$('[data-task="32"]').click();
  assert.ok(ctx.$('#task-dialog').hasAttribute('open'));
  const task = tasks.find((task) => task.id === 32);
  assert.equal(ctx.$$('.dialog-persona').length, task.personaCount);
  for (const persona of task.personas) assert.ok(ctx.$('#task-dialog-content').textContent.includes(persona.description));
  assert.equal(ctx.$('#task-dialog-content a').href, task.sourceUrl);
  ctx.document.dispatchEvent(new ctx.window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.equal(ctx.$('#task-dialog').hasAttribute('open'), false);
  assert.equal(ctx.document.body.classList.contains('dialog-open'), false);
  ctx.window.close();
});

test('rollout pairs are explicit placeholders and keyboard tabs work', async () => {
  const ctx = await boot();
  assert.equal(ctx.$$('.video-placeholder').length, 2);
  assert.equal(ctx.$$('video').length, 0);
  const tabs = ctx.$('.rollout-tabs');
  for (const [key, expected] of [['ArrowRight', '51'], ['End', '68'], ['Home', '18'], ['ArrowLeft', '68']]) {
    tabs.dispatchEvent(new ctx.window.KeyboardEvent('keydown', { key, bubbles: true }));
    const selected = ctx.$('[role="tab"][aria-selected="true"]');
    assert.equal(selected.dataset.example, expected);
    assert.equal(selected.tabIndex, 0);
    assert.equal(ctx.document.activeElement, selected);
    assert.equal(ctx.$('#rollout-panel').getAttribute('aria-labelledby'), selected.id);
    assert.equal(ctx.$$('.video-placeholder').length, 2);
  }
  ctx.window.close();
});

test('filled HTTPS and relative video slots render accessible native controls', async () => {
  const filled = structuredClone(examples);
  filled[0].personas[0].video = 'https://videos.example.test/a.mp4';
  filled[0].personas[1].video = 'videos/b.mp4';
  const ctx = await boot({ examples: filled });
  assert.equal(ctx.$$('video[controls][playsinline]').length, 2);
  assert.equal(ctx.$$('.video-placeholder').length, 0);
  assert.equal(ctx.$('video source').src, 'https://videos.example.test/a.mp4');
  assert.ok(ctx.$('.video-status').textContent.includes('Paired videos available'));
  ctx.window.close();
});

test('one filled video slot reports partial availability', async () => {
  const filled = structuredClone(examples);
  filled[0].personas[0].video = 'https://videos.example.test/a.mp4';
  const ctx = await boot({ examples: filled });
  assert.equal(ctx.$$('video').length, 1);
  assert.equal(ctx.$$('.video-placeholder').length, 1);
  assert.ok(ctx.$('.video-status').textContent.includes('1 of 2 videos available'));
  ctx.window.close();
});

test('GitHub Pages project subpaths preserve catalog, image, font CSS, script and video URLs', async () => {
  const base = 'https://hhd000exe.github.io/PersonaRobotBench-website/';
  const filled = structuredClone(examples);
  filled[0].personas[0].video = 'assets/rollouts/task18-A.mp4';
  const ctx = await boot({ url: base, examples: filled });
  assert.equal(ctx.ready, true);
  assert.deepEqual(ctx.requests, [base + 'data/tasks.json', base + 'data/examples.json', base + 'data/leaderboard.json']);
  assert.equal(ctx.$('.hero-scene').src, base + 'assets/hero-scene.webp');
  assert.equal(ctx.$('link[href="assets/fonts/fonts.css"]').href, base + 'assets/fonts/fonts.css');
  assert.equal(ctx.$('script[src="app.js"]').src, base + 'app.js');
  assert.equal(ctx.$('video source').src, base + 'assets/rollouts/task18-A.mp4');
  ctx.$('[data-example="68"]').click();
  assert.equal(ctx.$('.video-placeholder img').src, base + 'assets/task-scenes/task-068.webp');
  ctx.window.close();
});

test('unsafe video protocols never become source elements', async () => {
  for (const protocol of ['javascript:alert(1)', 'data:video/mp4;base64,AAAA', 'file:///tmp/private.mp4']) {
    const filled = structuredClone(examples);
    filled[0].personas[0].video = protocol;
    const ctx = await boot({ examples: filled });
    assert.equal(ctx.$$('video').length, 0);
    assert.equal(ctx.$$('.video-placeholder').length, 2);
    ctx.window.close();
  }
});

test('shipped examples provide six complete paired recordings with distinct real-frame posters', async () => {
  const ctx = await boot({ examples: shippedExamples });
  let count = 0;
  for (const taskId of [18, 51, 68]) {
    ctx.$('[data-example="' + taskId + '"]').click();
    const example = shippedExamples.find((item) => item.id === taskId);
    const videos = ctx.$$('video');
    assert.equal(videos.length, 2);
    assert.equal(ctx.$$('.video-placeholder').length, 0);
    for (const [index, video] of videos.entries()) {
      const persona = example.personas[index];
      assert.equal(video.querySelector('source').getAttribute('src'), 'https://benchmark.test/' + persona.video);
      assert.equal(video.querySelector('source').getAttribute('type'), 'video/mp4');
      assert.equal(video.poster, 'https://benchmark.test/' + persona.videoPoster);
      assert.notEqual(persona.videoPoster, example.poster);
      assert.equal(video.autoplay, false);
      assert.equal(video.hasAttribute('autoplay'), false);
      assert.ok(video.controls && video.playsInline);
      assert.ok(fs.statSync(path.join(root, persona.video)).size > 0);
      assert.ok(fs.statSync(path.join(root, persona.videoPoster)).size > 0);
      assert.ok(persona.videoDurationSeconds > 0);
      count++;
    }
    assert.ok(ctx.$('.video-status').textContent.includes('Paired videos available'));
    assert.ok(ctx.$('#rollout-recording-note').textContent.includes('Astra'));
    assert.ok(ctx.$('#rollout-recording-note').textContent.includes('1× simulation playback; inference waits omitted'));
    assert.equal(ctx.$('#rollout-recording-note a').href, 'https://benchmark.test/data/rollout-provenance.json');
    assert.equal(ctx.$('#rollout-recording-note').textContent.includes('Recorded as Task 110; now Task 51.'), taskId === 51);
  }
  assert.equal(count, 6);
  ctx.window.close();
});

test('switching rollout tabs pauses outgoing playback without autoplaying incoming videos', async () => {
  const ctx = await boot({ examples: shippedExamples });
  const outgoing = ctx.$$('video');
  for (const video of outgoing) Object.defineProperty(video, 'paused', { value: false });
  ctx.$('[data-example="51"]').click();
  assert.deepEqual(ctx.pausedVideos, outgoing);
  assert.ok(ctx.$$('video').every((video) => video.autoplay === false));
  assert.ok(outgoing.every((video) => !video.isConnected));
  ctx.window.close();
});

test('mobile menu toggles and navigation closes it', async () => {
  const ctx = await boot();
  ctx.$('.menu-toggle').click();
  assert.equal(ctx.$('#mobile-nav').hidden, false);
  assert.equal(ctx.$('.menu-toggle').getAttribute('aria-expanded'), 'true');
  ctx.$('#mobile-nav a').click();
  assert.equal(ctx.$('#mobile-nav').hidden, true);
  assert.equal(ctx.$('.menu-toggle').getAttribute('aria-expanded'), 'false');
  ctx.window.close();
});

test('copy button writes exact quick-start commands to clipboard', async () => {
  const ctx = await boot();
  let copied;
  Object.defineProperty(ctx.window.navigator, 'clipboard', { value: { writeText: async (text) => { copied = text; } } });
  ctx.$('#copy-code').click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(copied, ctx.$('#quickstart-code').textContent.trim());
  assert.equal(ctx.$('#copy-status').textContent, 'Commands copied.');
  ctx.window.close();
});

test('copy fallback selects commands when clipboard API is unavailable', async () => {
  const ctx = await boot();
  ctx.$('#copy-code').click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(ctx.window.getSelection().toString(), ctx.$('#quickstart-code').textContent);
  assert.ok(ctx.$('#copy-status').textContent.includes('Commands selected'));
  ctx.window.close();
});

test('fetch failures leave repository links and clear fallback state', async () => {
  const ctx = await boot({ fetchError: true });
  assert.equal(ctx.ready, false);
  assert.ok(ctx.$('#task-count').textContent.includes('unavailable'));
  assert.equal(ctx.$('#task-grid a').href, 'https://github.com/HHD000EXE/PersonaRobotBench-website/blob/website/data/tasks.json');
  assert.ok(ctx.$('#rollout-pair').textContent.includes('Recorded rollouts are unavailable'));
  assert.equal(ctx.$('#rollout-pair a').href, 'https://github.com/HHD000EXE/PersonaRobotBench-website/tree/website/assets/rollouts');
  ctx.window.close();
});

test('3D scene loads only on request, switches to image and resets camera', async () => {
  const c = await boot();
  assert.equal(c.$('model-viewer'), null);
  assert.equal(c.$('#model-viewer-library'), null);
  c.window.customElements.define('model-viewer', class extends c.window.HTMLElement {});
  c.$('#scene-toggle').click();
  const model = c.$('model-viewer');
  assert.equal(model.getAttribute('src'), 'assets/models/shared-desk.glb');
  model.dispatchEvent(new c.window.Event('load'));
  assert.equal(c.$('#scene-toggle').getAttribute('aria-pressed'), 'true');
  assert.equal(c.$('#scene-reset').disabled, false);
  model.setAttribute('camera-orbit', '90deg 70deg 3m');
  c.$('#scene-reset').click();
  assert.equal(model.getAttribute('camera-orbit'), '25deg 70deg 4.1m');
  c.$('#scene-toggle').click();
  assert.equal(c.$('#scene-toggle').getAttribute('aria-pressed'), 'false');
  assert.equal(c.$('#scene-reset').disabled, true);
  assert.equal(model.getAttribute('aria-hidden'), 'true');
  c.$('#scene-toggle').click();
  assert.equal(c.$('model-viewer'), model);
  assert.equal(c.$('#scene-viewport').classList.contains('is-3d'), true);
  c.dom.window.close();
});

test('3D model and library failures preserve image and permit retry', async () => {
  const c = await boot();
  c.$('#scene-toggle').click();
  c.$('#model-viewer-library').dispatchEvent(new c.window.Event('error'));
  await Promise.resolve(); await Promise.resolve();
  assert.equal(c.$('#scene-toggle').disabled, false);
  assert.match(c.$('#scene-status').textContent, /unavailable/);
  c.window.customElements.define('model-viewer', class extends c.window.HTMLElement {});
  c.$('#scene-toggle').click();
  c.$('model-viewer').dispatchEvent(new c.window.Event('error'));
  assert.equal(c.$('model-viewer'), null);
  assert.equal(c.$('#scene-viewport').classList.contains('is-3d'), false);
  assert.equal(c.$('#scene-toggle').disabled, false);
  assert.ok(c.$('.hero-scene'));
  c.dom.window.close();
});


test('leaderboard ranks only within each scoring criterion and shows settings and coverage', async () => {
  const ctx = await boot();
  assert.equal(ctx.leaderboardReady, true);
  assert.equal(ctx.$$('.leaderboard-board').length, 2);
  assert.deepEqual(ctx.$$('.leaderboard-board')[0].querySelectorAll('.leaderboard-bars > li').length, 3);
  assert.deepEqual(ctx.$$('.leaderboard-board:first-child .leaderboard-bars > li').map((row) => row.dataset.policy), ['second', 'first', 'pending']);
  assert.equal(ctx.$$('.leaderboard-board')[1].querySelector('.leaderboard-bars > li').dataset.policy, 'goal-policy');
  assert.match(ctx.$('.leaderboard-board').textContent, /77.7%/);
  assert.match(ctx.$('.leaderboard-board').textContent, /Not reported/);
  assert.match(ctx.$('.leaderboard-board').textContent, /Goal, process and fidelity must pass/);
  assert.match(ctx.$('.leaderboard-board').textContent, /3 trials \/ persona/);
  assert.match(ctx.$('.leaderboard-board').textContent, /100 tasks · 217 cases/);
  assert.match(ctx.$('#leaderboard-status').textContent, /2026-10-25/);
  assert.ok(ctx.$('figure.leaderboard-chart figcaption'));
  assert.ok(ctx.$('.leaderboard-bars[role="list"]'));
  assert.equal(ctx.$('#leaderboard a[download]').getAttribute('href'), 'data/leaderboard.json');
  ctx.window.close();
});

test('leaderboard failure leaves the catalog, task dialog and recording tabs usable', async () => {
  const ctx = await boot({ leaderboardError: true });
  assert.equal(ctx.ready, true);
  assert.equal(ctx.leaderboardReady, false);
  assert.match(ctx.$('#leaderboard-status').textContent, /unavailable/);
  assert.equal(ctx.$('#leaderboard-boards a').getAttribute('href'), 'data/leaderboard.json');
  input(ctx, '14');
  ctx.$('[data-task="14"]').click();
  assert.ok(ctx.$('#task-dialog').hasAttribute('open'));
  ctx.$('.dialog-close').click();
  ctx.$('[data-example="51"]').click();
  assert.match(ctx.$('#rollout-id').textContent, /051/);
  ctx.window.close();
});

test('catalog failure does not suppress available leaderboard results', async () => {
  const ctx = await boot({ catalogError: true });
  assert.equal(ctx.ready, false);
  assert.equal(ctx.leaderboardReady, true);
  assert.equal(ctx.$$('.leaderboard-board').length, 2);
  assert.match(ctx.$('#task-count').textContent, /unavailable/);
  ctx.window.close();
});

test('invalid leaderboard scores fail visibly without publishing a misleading chart', async () => {
  const invalid = structuredClone(leaderboardFixture);
  invalid.boards[0].rows[0].scorePercent = 120;
  const ctx = await boot({ leaderboard: invalid });
  assert.equal(ctx.leaderboardReady, false);
  assert.equal(ctx.$$('.leaderboard-chart').length, 0);
  assert.equal(ctx.ready, true);
  ctx.window.close();
});

test('leaderboard text is escaped before rendering source-authored notes', async () => {
  const injected = structuredClone(leaderboardFixture);
  injected.boards[0].rows[0].policy = '<img src=x onerror=alert(1)>';
  injected.boards[0].notes = ['<script>alert(1)</script>'];
  const ctx = await boot({ leaderboard: injected });
  assert.equal(ctx.leaderboardReady, true);
  assert.equal(ctx.$('#leaderboard-boards img'), null);
  assert.equal(ctx.$('#leaderboard-boards script'), null);
  assert.ok(ctx.$('#leaderboard-boards').textContent.includes('<img src=x onerror=alert(1)>'));
  assert.ok(ctx.$('#leaderboard-boards').textContent.includes('<script>alert(1)</script>'));
  ctx.window.close();
});


test('published policy snapshot renders its reported scores and settings without special Astra labeling', async () => {
  const ctx = await boot({ leaderboard: shippedLeaderboard });
  assert.equal(ctx.leaderboardReady, true);
  assert.equal(ctx.$$('.leaderboard-board').length, shippedLeaderboard.boards.length);
  for (const [index, board] of shippedLeaderboard.boards.entries()) {
    const section = ctx.$$('.leaderboard-board')[index];
    const expected = [...board.rows].sort((a, b) => (b.scorePercent ?? -1) - (a.scorePercent ?? -1));
    const actual = [...section.querySelectorAll('.leaderboard-bars > li')];
    assert.deepEqual(actual.map((row) => row.dataset.policy), expected.map((row) => row.id));
    for (const [i, row] of expected.entries()) {
      assert.equal(actual[i].querySelector('.leaderboard-policy').textContent, row.policy);
      assert.equal(actual[i].querySelector('.leaderboard-score').textContent, row.scorePercent === null ? 'Not reported' : row.scorePercent.toFixed(1) + '%');
      assert.ok(actual[i].textContent.includes(row.variant));
      const settings = section.querySelectorAll('.leaderboard-protocol')[i];
      assert.ok(settings.textContent.includes(row.policy));
      assert.ok(settings.textContent.includes(row.variant));
      assert.ok(settings.textContent.includes(row.coverage));
      assert.ok(settings.textContent.includes(row.protocol));
    }
  }
  const astra = ctx.$('[data-policy="astra-high"]');
  assert.equal(astra.querySelector('.leaderboard-policy').textContent, 'Astra');
  assert.doesNotMatch(astra.textContent, /author.reported|not independently|not recomputed|unverified/i);
  assert.equal(ctx.$('#leaderboard a[href="data/leaderboard-results.json"]').hasAttribute('download'), true);
  ctx.window.close();
});


test('leaderboard appears between the hero and section 01, with navigation in page order', async () => {
  const ctx = await boot();
  const sections = [...ctx.$('main').children].filter((node) => node.tagName === 'SECTION');
  assert.ok(sections[0].classList.contains('hero'));
  assert.equal(sections[1].id, 'leaderboard');
  assert.equal(sections[2].id, 'overview');
  assert.match(ctx.$('#overview .eyebrow').textContent, /^01 /);
  assert.equal(ctx.$('#leaderboard .eyebrow').textContent, 'POLICY RESULTS');
  assert.match(ctx.$('#resources .eyebrow').textContent, /^05 /);
  for (const nav of ctx.$$('.desktop-nav, .mobile-nav')) assert.equal(nav.querySelector('a').getAttribute('href'), '#leaderboard');
  ctx.window.close();
});

test('bar lengths share a zero-based scale and pending policies have no quantitative bar', async () => {
  const ctx = await boot({ leaderboard: shippedLeaderboard });
  const chart = ctx.$('.leaderboard-chart');
  assert.equal(chart.dataset.axisMax, '40');
  const ticks = [...chart.querySelectorAll('.leaderboard-axis-track > span')];
  assert.deepEqual(ticks.map((tick) => tick.textContent), ['0%', '10%', '20%', '30%', '40%']);
  assert.match(chart.querySelector('figcaption').textContent, /Scale: 0 to 40 percent/);
  const high = ctx.$('[data-policy="astra-high"]');
  assert.equal(high.querySelector('.leaderboard-bar-fill').style.width, '83%');
  assert.equal(high.querySelector('.leaderboard-score').textContent, '33.2%');
  const pending = ctx.$('[data-policy="gemini4"]');
  assert.equal(pending.querySelector('.leaderboard-bar-lane'), null);
  assert.equal(pending.querySelector('.leaderboard-score').textContent, 'Not reported');
  assert.ok(ctx.$('details.leaderboard-protocols > summary'));
  ctx.window.close();
});

test('bar scales remain finite for zero, pending and 100 percent scores', async () => {
  for (const scores of [[0, null, 0], [null, null, null], [0, null, 100]]) {
    const data = structuredClone(leaderboardFixture);
    data.boards = [data.boards[0]];
    data.boards[0].rows.forEach((row, i) => { row.scorePercent = scores[i]; });
    const ctx = await boot({ leaderboard: data });
    assert.equal(ctx.leaderboardReady, true);
    assert.equal(ctx.$('.leaderboard-chart').dataset.axisMax, scores.includes(100) ? '100' : '10');
    assert.equal(ctx.$$('.leaderboard-bar-fill').length, scores.filter((score) => score !== null).length);
    for (const bar of ctx.$$('.leaderboard-bar-fill')) assert.ok(['0%', '100%'].includes(bar.style.width));
    ctx.window.close();
  }
});
