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
const examples = JSON.parse(fs.readFileSync(path.join(root, 'data/examples.json'), 'utf8'));
// Placeholder behavior must remain testable after contributors add real videos.
// These fixtures never modify the published examples file.
for (const example of examples) {
  for (const persona of example.personas) persona.video = null;
}

async function boot(options = {}) {
  const dom = new JSDOM(html, { url: options.url || 'https://benchmark.test/', runScripts: 'outside-only', pretendToBeVisual: true });
  const { window } = dom;
  const requests = [];
  window.fetch = async (url) => {
    requests.push(new URL(url, window.location.href).href);
    return { ok: !options.fetchError, json: async () => structuredClone(url.includes('tasks.json') ? tasks : (options.examples || examples)) };
  };
  window.eval(app);
  const ready = await window.prbReady;
  return { dom, window, requests, document: window.document, ready, $: (selector) => window.document.querySelector(selector), $$: (selector) => [...window.document.querySelectorAll(selector)] };
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
  assert.deepEqual(ctx.requests, [base + 'data/tasks.json', base + 'data/examples.json']);
  assert.equal(ctx.$('.hero-scene').src, base + 'assets/hero-scene.webp');
  assert.equal(ctx.$('link[href="assets/fonts/fonts.css"]').href, base + 'assets/fonts/fonts.css');
  assert.equal(ctx.$('script[src="app.js"]').src, base + 'app.js');
  assert.equal(ctx.$('video source').src, base + 'assets/rollouts/task18-A.mp4');
  ctx.$('[data-example="68"]').click();
  assert.equal(ctx.$('.video-placeholder img').src, base + 'assets/task-068.webp');
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
  assert.ok(ctx.$('#rollout-pair').textContent.includes('will be added'));
  ctx.window.close();
});
