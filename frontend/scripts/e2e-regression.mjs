#!/usr/bin/env node
/**
 * Browser regression checks for the Beacon React UI — no test framework, no new
 * dependencies. Drives a real headless Chrome over the DevTools Protocol against
 * the running app, and uses request interception to simulate the backend being
 * unreachable or failing. The concierge endpoint is MOCKED, so this never reaches
 * Amazon Bedrock.
 *
 * Covers:
 *   1. Retry recovery: success → change input while offline → return to the cached
 *      inputs → Retry must make a real request and clear offline only on success.
 *   2. A non-connection evaluation error leaves an older reading on screen and
 *      disables the concierge until a retry succeeds.
 *   3. Retrying a failed damage-preset load for a newly selected household.
 *   4. Declared needs: guidance changes, numbers do not, earlier answers are
 *      separated, notices are tailored, reset clears everything.
 *   5. "Estimate updated" delivery decision matches the API response (material,
 *      unchanged, no baseline).
 *   No automatic concierge calls happen at any point.
 *
 * Prereqs: Python API on :8000 and `npm run dev` (or `npm start`) on :3000.
 * Run:     npm run test:e2e        (Node 20 needs --experimental-websocket; the script sets it)
 * Env:     BASE_URL (default http://localhost:3000), CHROME_PATH (auto-detected on macOS)
 */
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000';
const CANDIDATES = [
  process.env.CHROME_PATH,
  ...(() => {
    const root = path.join(os.homedir(), 'Library/Caches/ms-playwright');
    try {
      return fs
        .readdirSync(root)
        .filter((d) => d.startsWith('chromium_headless_shell'))
        .sort()
        .reverse()
        .map((d) => path.join(root, d, 'chrome-headless-shell-mac-arm64/chrome-headless-shell'));
    } catch {
      return [];
    }
  })(),
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
].filter(Boolean);
const CHROME = CANDIDATES.find((p) => fs.existsSync(p));
if (!CHROME) {
  console.error('No Chrome/Chromium found. Set CHROME_PATH.');
  process.exit(2);
}
if (typeof WebSocket === 'undefined') {
  console.error('This Node has no global WebSocket. Use Node 22+, or Node 20 with --experimental-websocket.');
  process.exit(2);
}

// ---------------------------------------------------------------------------
// Minimal CDP client
// ---------------------------------------------------------------------------
const port = 9400 + Math.floor(Math.random() * 400);
const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'beacon-e2e-'));
const chrome = spawn(
  CHROME,
  [`--remote-debugging-port=${port}`, '--headless=new', '--no-first-run', '--no-default-browser-check', `--user-data-dir=${profile}`, 'about:blank'],
  { stdio: 'ignore' }
);
const cleanup = () => {
  try {
    chrome.kill();
  } catch {}
  try {
    fs.rmSync(profile, { recursive: true, force: true });
  } catch {}
};
process.on('exit', cleanup);

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let targets;
for (let i = 0; i < 50; i++) {
  try {
    targets = await (await fetch(`http://127.0.0.1:${port}/json`)).json();
    if (targets.some((t) => t.type === 'page')) break;
  } catch {}
  await sleep(200);
}
const ws = new WebSocket(targets.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((r, j) => {
  ws.onopen = r;
  ws.onerror = j;
});
let nextId = 0;
const pending = new Map();
const listeners = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    pending.get(m.id)(m);
    pending.delete(m.id);
  } else if (m.method) listeners.forEach((fn) => fn(m));
};
const send = (method, params = {}) =>
  new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, (m) => (m.error ? reject(new Error(`${method}: ${m.error.message}`)) : resolve(m.result)));
    ws.send(JSON.stringify({ id, method, params }));
  });
const js = async (expr) => {
  const r = await send('Runtime.evaluate', { expression: `(() => { ${expr} })()`, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error(`page error: ${r.exceptionDetails.exception?.description || r.exceptionDetails.text}`);
  return r.result.value;
};
async function waitFor(desc, expr, timeout = 20000) {
  const t0 = Date.now();
  let last;
  while (Date.now() - t0 < timeout) {
    last = await js(expr).catch((e) => String(e));
    if (last === true) return;
    await sleep(150);
  }
  throw new Error(`Timed out waiting for: ${desc} (last=${JSON.stringify(last)})`);
}

// ---------------------------------------------------------------------------
// Backend simulation via request interception
// ---------------------------------------------------------------------------
const net = { mode: 'up', log: [], previews: [] }; // mode: up | down | eval500
listeners.push(async (m) => {
  if (m.method !== 'Fetch.requestPaused') return;
  const { requestId, request, responseStatusCode } = m.params;
  const url = new URL(request.url);
  if (responseStatusCode !== undefined) {
    // Response stage (notification previews only): capture what the UI received.
    try {
      const b = await send('Fetch.getResponseBody', { requestId });
      net.previews.push(JSON.parse(b.base64Encoded ? Buffer.from(b.body, 'base64').toString() : b.body));
    } catch {}
    return send('Fetch.continueRequest', { requestId }).catch(() => {});
  }
  net.log.push({ path: url.pathname, body: request.postData ?? null, mode: net.mode, t: Date.now() });
  if (url.pathname.startsWith('/api/concierge/ask')) {
    const body = JSON.stringify({ text: 'Mock answer (e2e).', mode: 'fallback', provider_error: 'mocked in e2e', used_counterfactual: false });
    return send('Fetch.fulfillRequest', {
      requestId,
      responseCode: 200,
      responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
      body: Buffer.from(body).toString('base64'),
    }).catch(() => {});
  }
  if (net.mode === 'down') return send('Fetch.failRequest', { requestId, errorReason: 'ConnectionRefused' }).catch(() => {});
  if (net.mode === 'eval500' && url.pathname === '/api/evaluate') {
    return send('Fetch.fulfillRequest', {
      requestId,
      responseCode: 500,
      responseHeaders: [{ name: 'Content-Type', value: 'application/json' }],
      body: Buffer.from(JSON.stringify({ detail: 'Simulated engine fault' })).toString('base64'),
    }).catch(() => {});
  }
  return send('Fetch.continueRequest', { requestId }).catch(() => {});
});
await send('Fetch.enable', {
  patterns: [
    { urlPattern: '*/api/*', requestStage: 'Request' },
    { urlPattern: '*/api/notification-preview*', requestStage: 'Response' },
  ],
});
await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });

const count = (p, since = 0) => net.log.filter((r) => r.path.startsWith(p) && r.t >= since).length;

// ---------------------------------------------------------------------------
// Page helpers (DOM queries run inside the page)
// ---------------------------------------------------------------------------
const H = `
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const banner = () => $$('[role=alert]').find(e => /Engine disconnected — Beacon shows no estimates/.test(e.textContent));
  const readingAlert = () => $$('#reading [role=alert]')[0];
  const reading = () => $('#reading')?.innerText || '';
  const btn = (label) => $$('button').find(b => b.getAttribute('aria-label') === label || b.textContent.trim() === label);
  const suggest = () => $$('#ask .suggest');
  const askStatus = () => $('#ask p[role=status]')?.textContent || '';
  const crewValue = () => (reading().match(/(\\d+) crews?, access/) || [])[1];
  const needBox = (text) => $$('label').find(l => l.textContent.includes(text))?.querySelector('input');
  const checklist = () => $$('.notebook li label').map(l => l.textContent.trim());
  const restoration = () => { const t = reading(); const a = t.indexOf('heuristic scenario band'); const b = t.indexOf('An unvalidated heuristic'); return t.slice(a, b).trim(); };
  const band = () => (reading().match(/Outage-risk band\\s+(\\w+)/i) || [])[1];
  const idle = () => !!$('#reading') && !/Updating reading/.test(reading()) && !/Reading the scenario/.test(reading());
`;
const page = (body) => js(H + body);
const until = (desc, body, t) => waitFor(desc, H + body, t);

async function load() {
  net.mode = 'up';
  await send('Page.navigate', { url: BASE_URL + '/' });
  await until('first reading', `return idle() && /crews?, access/.test(reading());`, 90000);
  await sleep(400);
}
async function setSelect(id, value) {
  await page(`
    const el = document.getElementById(${JSON.stringify(id)});
    const setter = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, 'value').set;
    setter.call(el, ${JSON.stringify(value)});
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return true;`);
}

const results = [];
async function check(name, fn) {
  const t0 = Date.now();
  try {
    await fn();
    results.push({ name, ok: true });
    console.log(`PASS ${name} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  } catch (e) {
    results.push({ name, ok: false, err: e.message });
    console.log(`FAIL ${name}\n     ${e.message}`);
  }
}
const assert = (cond, msg) => {
  if (!cond) throw new Error(msg);
};

// ---------------------------------------------------------------------------
// 1. Retry recovery after returning to the cached inputs
// ---------------------------------------------------------------------------
await check('retry recovers after returning to the cached inputs', async () => {
  await load();
  const startCrews = await page(`return crewValue();`);
  net.mode = 'down';
  await page(`btn('One more crew').click(); return true;`);
  await until('offline banner', `return !!banner();`);
  assert(await page(`return suggest().every(b => b.disabled);`), 'concierge must be disabled while offline');
  await page(`btn('One fewer crew').click(); return true;`);
  await sleep(700);
  assert((await page(`return crewValue();`)) === startCrews, 'reading should show the cached inputs again');
  assert(await page(`return !!banner();`), 'still offline: nothing has proven the engine is back');
  assert(await page(`return suggest().every(b => b.disabled);`), 'concierge stays disabled while offline');

  net.mode = 'up';
  const before = Date.now();
  await page(`$$('button', banner()).find(b => /Retry/.test(b.textContent)).click(); return true;`);
  await until('banner cleared after a successful request', `return !banner();`);
  assert(count('/api/evaluate', before) >= 1, 'Retry must make a real /api/evaluate request');
  assert(await page(`return !readingAlert();`), 'reading alert should be gone');
  await until('concierge re-enabled', `return suggest().length > 0 && suggest().every(b => !b.disabled);`);
});

// The fix must not clear "offline" without a successful request.
await check('a failed retry stays offline', async () => {
  await load();
  net.mode = 'down';
  await page(`btn('One more crew').click(); return true;`);
  await until('offline banner', `return !!banner();`);
  const before = Date.now();
  await page(`$$('button', banner()).find(b => /Retry/.test(b.textContent)).click(); return true;`);
  await until('retry attempted', `return !/Retrying/.test(banner()?.textContent || '');`);
  assert(count('/api/evaluate', before) >= 1, 'retry must attempt a request');
  assert(await page(`return !!banner();`), 'must remain offline after a failed retry');
  net.mode = 'up';
});

// ---------------------------------------------------------------------------
// 2. Evaluation error (not a connection failure) disables the concierge
// ---------------------------------------------------------------------------
await check('evaluation error keeps concierge disabled until retry succeeds', async () => {
  await load();
  net.mode = 'eval500';
  await page(`btn('One more crew').click(); return true;`);
  await until('reading error alert', `return !!readingAlert() && /Couldn.t update/.test(readingAlert().textContent);`);
  assert(await page(`return !banner();`), 'a 500 is not a connection failure');
  assert(await page(`return suggest().every(b => b.disabled);`), 'concierge must be disabled for a stale reading');
  assert(/match your current controls/.test(await page(`return askStatus();`)), 'explains why asking is disabled');
  net.mode = 'up';
  await page(`$$('button', readingAlert()).find(b => /Retry/.test(b.textContent)).click(); return true;`);
  await until('alert cleared', `return !readingAlert() && idle();`);
  await until('concierge enabled', `return suggest().every(b => !b.disabled);`);
});

// ---------------------------------------------------------------------------
// 3. Retry a failed preset load for a newly selected household
// ---------------------------------------------------------------------------
await check('retry reloads presets for a newly selected household', async () => {
  await load();
  const second = await page(`return $$('#household option')[1]?.value;`);
  assert(second, 'need a second household');
  net.mode = 'down';
  await setSelect('household', second);
  await until('offline banner', `return !!banner();`);
  net.mode = 'up';
  const before = Date.now();
  await page(`$$('button', banner()).find(b => /Retry/.test(b.textContent)).click(); return true;`);
  await until('recovered on the new household', `return !banner() && idle() && /Real premise 2|Household B/.test(reading());`, 30000);
  assert(count('/api/damage-scenarios/', before) >= 1, 'presets must be re-requested');
  assert(count('/api/evaluate', before) >= 1, 'the new household must be evaluated');
});

// ---------------------------------------------------------------------------
// 4. Declared needs + reset (+ concierge context identity, mocked answers)
// ---------------------------------------------------------------------------
await check('declared needs tailor guidance only; reset clears them', async () => {
  await load();
  const askBefore = count('/api/concierge/ask');
  assert(askBefore === 0, `no automatic concierge calls (saw ${askBefore})`);
  assert(await page(`return !needBox('electricity-dependent medical').checked && !needBox('accessibility assistance').checked;`), 'both start unchecked');
  const rest0 = await page(`return restoration();`);
  const band0 = await page(`return band();`);
  const list0 = await page(`return checklist();`);

  await page(`suggest()[0].click(); return true;`);
  await until('mock answer shown', `return /Mock answer/.test($('[role=log]').innerText);`);

  const t = Date.now();
  await page(`needBox('electricity-dependent medical').click(); return true;`);
  await until('re-evaluated with needs', `return idle() && /Tailored for what you declared/.test(reading());`);
  const evalReq = net.log.filter((r) => r.path === '/api/evaluate' && r.t >= t).pop();
  assert(evalReq && JSON.parse(evalReq.body).declared_needs?.medical_equipment === true, 'request carries the declaration');
  assert((await page(`return restoration();`)) === rest0, 'restoration must not change');
  assert((await page(`return band();`)) === band0, 'risk band must not change');
  const list1 = await page(`return checklist();`);
  assert(/electrically powered medical equipment/.test(list1[0]), `needs guidance first, got: ${list1[0]}`);
  assert(list1.length > list0.length, 'checklist gains guidance');
  assert(/Declared needs[\s\S]*None declared[\s\S]*Medical equipment/.test(await page(`return reading();`)), 'What changed lists the declaration');
  assert(/stayed the same/.test(await page(`return reading();`)), 'engine reading unchanged');
  await until('earlier answer separated', `return /Earlier answers — about a different scenario \\(1\\)/.test($('[role=log]').innerText);`);

  // Notice wording is tailored.
  await page(`document.querySelector('input[name=lifecycle][value=outage_confirmed]').click(); return true;`);
  await until('tailored notice', `return /electricity-dependent medical equipment/.test(document.querySelector('[aria-label="Notice preview text"]')?.textContent || '');`);

  await page(`btn('Reset scenario').click(); return true;`);
  await until('reset applied', `return idle() && !needBox('electricity-dependent medical').checked && !/Tailored for what you declared/.test(reading());`);
  assert((await page(`return $('[role=log]').innerText;`)).includes('Nothing is sent until you ask'), 'chat cleared');
  assert(JSON.stringify(await page(`return checklist();`)) === JSON.stringify(list0), 'checklist back to scenario guidance');
  assert(count('/api/concierge/ask') === 1, 'only the one explicit question reached the concierge');
});

// ---------------------------------------------------------------------------
// 5. "Estimate updated" delivery decision matches the API response
// ---------------------------------------------------------------------------
await check('estimate-update delivery decision mirrors the returned preview', async () => {
  await load();
  await setSelect('preset', 'multi_damage');
  await until('multi_damage reading', `return idle() && /Widespread damage/.test(reading());`);
  const setCrews = async (n) => {
    while ((await page(`return crewValue();`)) !== String(n)) {
      const cur = Number(await page(`return crewValue();`));
      await page(`btn('${cur > n ? 'One fewer crew' : 'One more crew'}').click(); return true;`);
      await until(`${cur > n ? cur - 1 : cur + 1} crews`, `return idle() && crewValue() === '${cur > n ? cur - 1 : cur + 1}';`);
    }
  };
  await setCrews(1);
  await page(`document.querySelector('input[name=lifecycle][value=restoration_updated]').click(); return true;`);

  const decision = async (desc, expect) => {
    await until(`${desc}: preview for the current reading`,
      `return idle() && !!document.querySelector('[aria-label="Notice preview text"]') && !/Refreshing preview/.test(document.body.innerText);`);
    await sleep(300);
    const p = net.previews.filter((x) => x.lifecycle_state === 'restoration_updated').pop();
    assert(p, `${desc}: captured a restoration_updated preview`);
    assert(p.estimate_change.kind === expect.kind, `${desc}: kind=${p.estimate_change.kind}`);
    assert(p.estimate_change.material === expect.material, `${desc}: material=${p.estimate_change.material}`);
    assert(p.send_recommended === expect.send, `${desc}: send_recommended=${p.send_recommended}`);
    const ui = await page(`return document.querySelector('#notices').innerText;`);
    assert(ui.includes(p.send_recommended ? 'A send would be recommended' : 'No send recommended'), `${desc}: UI decision text`);
    for (const b of p.send_blockers) assert(ui.includes(b), `${desc}: blocker shown: ${b}`);
    const ledger = p.estimate_change.kind === 'no_previous' ? 'No baseline' : p.estimate_change.material ? 'Material' : 'Not material';
    assert(new RegExp(`Estimate change\\s+${ledger}`).test(ui), `${desc}: ledger shows ${ledger}`);
    // The phone animates old → new text (AnimatePresence), so poll until the new text is the one on screen.
    await until(`${desc}: phone shows the returned message`,
      `return [...document.querySelectorAll('[aria-label="Notice preview text"]')].some(e => e.textContent === ${JSON.stringify(p.message)});`);
  };

  await setCrews(2);
  await decision('1→2 crews', { kind: 'changed', material: true, send: true });
  await setCrews(3);
  await setCrews(4);
  await decision('3→4 crews', { kind: 'unchanged', material: false, send: false });
  await page(`btn('Reset scenario').click(); return true;`);
  await until('reset', `return idle() && !/Widespread damage/.test(reading());`);
  await page(`document.querySelector('input[name=lifecycle][value=restoration_updated]').click(); return true;`);
  await decision('after reset', { kind: 'no_previous', material: false, send: false });
});

assert(count('/api/concierge/ask') <= 1, 'no automatic concierge calls');
const failed = results.filter((r) => !r.ok);
console.log(`\n${results.length - failed.length}/${results.length} browser regression checks passed`);
ws.close();
cleanup();
process.exit(failed.length ? 1 : 0);
