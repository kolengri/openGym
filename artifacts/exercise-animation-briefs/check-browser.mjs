// Exercise the actual offline artifact in an isolated browser. No app server or media.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { homedir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';

const moduleUrl = process.env.BRIEFS_PLAYWRIGHT
  ? pathToFileURL(process.env.BRIEFS_PLAYWRIGHT).href
  : new URL('../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs', import.meta.url).href;
const { chromium } = await import(moduleUrl);
const executablePath = process.env.BRIEFS_CHROME || `${homedir()}/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell`;
const root = new URL('.', import.meta.url);
const index = new URL('index.html', root).href;
const coverage = JSON.parse(fs.readFileSync(new URL('coverage-report.json', root), 'utf8'));
const browser = await chromium.launch({ executablePath, headless: true });
const errors = [];
const warnings = [];
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text());
    if (message.type() === 'warning') warnings.push(message.text());
  });
  await page.goto(index);
  await page.locator('#detail h2').waitFor();
  assert.match(await page.locator('#summary').innerText(), /6,554/);
  assert.match(await page.locator('#detail h2').innerText(), /5965/);
  assert.equal(await page.locator('#list a').count(), 100);
  await page.locator('#next').click();
  assert.match(await page.locator('#count').innerText(), /Page 2/);
  await page.locator('#status').selectOption('proposal_ready_for_review');
  assert.ok((await page.locator('#count').innerText()).startsWith(coverage.canonical_storyboard_readiness_counts.proposal_ready_for_review.toLocaleString()));
  await page.locator('#status').selectOption('equipment_free');
  assert.equal(await page.locator('#list a[data-id="4209"]').count(), 0);
  assert.equal(await page.locator('#list a[data-id="5915"]').count(), 1);
  await page.goto(`${index}#0004`);
  assert.match(await page.locator('#detail').innerText(), /Alias 0004 resolves to canonical 5266/);
  await page.locator('#status').selectOption('');
  await page.locator('#query').fill('0002');
  await page.locator('#list a[data-id="0002"]').click();
  await page.waitForFunction(() => document.querySelector('#detail h2')?.textContent.startsWith('0002'));
  assert.match(await page.locator('#detail').innerText(), /prop_text_conflict/);
  const jsonPath = await page.locator('#detail a').filter({ hasText: 'Compressed JSON download' }).getAttribute('href');
  assert.ok(fs.existsSync(fileURLToPath(new URL(jsonPath, root))));
  await page.screenshot({ path: fileURLToPath(new URL('index-desktop.png', root)), fullPage: true });
  await page.locator('#detail a').filter({ hasText: 'Read full movement' }).click();
  await page.waitForLoadState('load');
  const article = page.locator('article[id="0002"]');
  assert.match(await article.innerText(), /Do not add the bench/);
  assert.match(await article.innerText(), /Proposed staging/);
  assert.match(await article.innerText(), /Complete ordered source instructions/);
  const download = await article.getByRole('link', { name: /Full JSON chunk download/ }).getAttribute('href');
  assert.ok(fs.existsSync(fileURLToPath(new URL(download, page.url()))));
  await page.goto(`${index}#9066`);
  await page.setViewportSize({ width: 360, height: 800 });
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await page.locator('#detail a').filter({ hasText: 'Read full movement' }).click();
  await page.waitForLoadState('load');
  assert.match(await page.locator('article[id="9066"]').innerText(), /authored_laterality_and_contacts/);
  const dimensions = await page.evaluate(() => ({
    url: location.href, width: innerWidth, scroll: document.documentElement.scrollWidth,
    overflowing: [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > innerWidth).slice(0, 8).map(e => ({tag: e.tagName, text: e.textContent.slice(0, 180), right: e.getBoundingClientRect().right})),
  }));
  assert.ok(dimensions.scroll <= dimensions.width, JSON.stringify(dimensions));
  assert.deepEqual(errors, []);
  assert.deepEqual(warnings, []);
  const report = {
    passed: true, browser: await browser.version(), mode: 'isolated headless Chromium; file:// offline artifacts',
    checks: ['Initial rendering and 100-record pagination', 'Separate source/storyboard filters',
      'Equipment-free candidates exclude box jump', 'Alias resolution', 'Search and canonical selection',
      'Conflict shown in actual readable detail page', 'Compressed JSON download targets exist',
      'Authored first-five placement visible', '360px index and detail without horizontal overflow'],
    console_errors: errors, console_warnings: warnings,
    screenshot: 'index-desktop.png',
  };
  fs.writeFileSync(new URL('browser-verification.json', root), `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`${JSON.stringify(report, null, 2)}\n`);
} finally {
  await browser.close();
}
