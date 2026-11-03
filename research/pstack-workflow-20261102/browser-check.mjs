import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';

const require = createRequire(import.meta.url);
const { chromium } = require('/home/ytian9405/lemo-opuscar/node_modules/playwright-core');
const root = path.dirname(fileURLToPath(import.meta.url));
const data = JSON.parse(await readFile(path.join(root, 'workflow-data.json'), 'utf8'));
assert.equal(data.flows.length, 23);
assert.equal(Object.values(data.skills).filter(s => s.kind === 'skill').length, 34);
assert.equal(data.principles.length, 24);
assert.equal(new Set(data.flows.map(f => f.id)).size, 23);
for (const f of [...data.flows, ...data.extra]) {
  for (const s of f.steps) {
    if (s.skill) assert.ok(data.skills[s.skill], `${f.id}: unresolved skill ${s.skill}`);
  }
}
const browser = await chromium.launch({
  executablePath: '/home/ytian9405/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell',
  headless: true,
  args: ['--no-sandbox'],
  env: { ...process.env, LD_LIBRARY_PATH: '/tmp/xhs-browser-libs/usr/lib/x86_64-linux-gnu' },
});
const context = await browser.newContext({ viewport: { width: 1720, height: 1200 }, deviceScaleFactor: 1 });
const page = await context.newPage();
const errors = [], remoteRequests = [];
page.on('pageerror', e => errors.push(e.message));
page.on('request', r => { if (/^https?:/.test(r.url())) remoteRequests.push(r.url()); });
await page.goto(new URL('./index.html', import.meta.url).href);
await page.locator('.graph svg').waitFor();
await page.screenshot({ path: path.join(root, 'overview.png'), fullPage: true });
await writeFile(path.join(root, 'overview.svg'), await page.locator('.graph svg').evaluate(el => {
  const copy = el.cloneNode(true);
  const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  style.textContent = 'text{font-family:"Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif}.edge{fill:none;stroke:#92a5ad;stroke-width:1.6}.edge.conditional{stroke-dasharray:5 5}.edgeLabel{font-size:10px;fill:#526a76;paint-order:stroke;stroke:#fff;stroke-width:5px;stroke-linejoin:round}';
  copy.prepend(style);
  return copy.outerHTML;
}));
let checkedNodes = 0;
for (const f of data.flows) {
  await page.evaluate(id => window.PSTACK.selectFlow(id), f.id);
  assert.equal(await page.locator('.graph .node').count(), f.steps.length);
  for (const s of f.steps.filter(s => s.skill)) {
    await page.locator(`.graph [data-skill="${s.skill}"]`).first().click();
    assert.equal(await page.locator('#detail h2').innerText(), s.skill);
    checkedNodes++;
  }
}
await page.evaluate(() => window.PSTACK.selectFlow('feature'));
await page.locator('#focus').click();
assert.equal(await page.locator('.graph.focus-only').count(), 1);
await page.locator('#focus').click();
await page.screenshot({ path: path.join(root, 'feature.png'), fullPage: true });
await page.evaluate(() => window.PSTACK.selectMode('interest'));
assert.equal(await page.locator('.skillcard').count(), 15);
for (const f of data.extra) {
  await page.locator(`[data-extra="${f.id}"]`).click();
  assert.equal(await page.locator('.graph .node').count(), f.steps.length);
  if (f.id === 'teach') await page.screenshot({ path: path.join(root, 'teach.png'), fullPage: true });
}
await page.evaluate(() => window.PSTACK.selectMode('principles'));
assert.equal(await page.locator('.skillcard').count(), 24);
await page.locator('#search').fill('redesign');
assert.equal(await page.locator('.skillcard').count(), 1);
await page.locator('.skillcard').click();
assert.equal(await page.locator('#detail h2').innerText(), 'principle-redesign-from-first-principles');
await page.evaluate(() => window.PSTACK.selectMode('catalog'));
assert.equal(await page.locator('.skillcard').count(), 34);
await page.evaluate(() => window.PSTACK.selectMode('overview'));
const firstNode = page.locator('.graph [data-skill="setup-pstack"]');
await firstNode.focus();
await page.keyboard.press('Enter');
assert.equal(await page.locator('#detail h2').innerText(), 'setup-pstack');
await page.setViewportSize({ width: 390, height: 844 });
await page.evaluate(() => window.PSTACK.selectFlow('feature'));
await page.locator('#mobileMenu').selectOption('investigation');
assert.equal(await page.locator('#content h2').innerText(), '只读调查');
const widths = await page.evaluate(() => ({ page: document.documentElement.scrollWidth, viewport: innerWidth }));
assert.ok(widths.page <= widths.viewport + 1, `mobile overflow: ${JSON.stringify(widths)}`);
await page.screenshot({ path: path.join(root, 'mobile.png'), fullPage: true });
assert.deepEqual(errors, []);
assert.deepEqual(remoteRequests, []);
const result = { playbooks: 23, compositionPaths: data.extra.length, skillNodesClicked: checkedNodes, tools: 34, principles: 24, interestCards: 15, mobileWidths: widths, pageErrors: errors, remoteRequests };
await writeFile(path.join(root, 'verification.json'), JSON.stringify(result, null, 2));
console.log(JSON.stringify(result));
await browser.close();
