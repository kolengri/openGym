import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { chromium } from '../first-exercise-3d/runtime/node_modules/playwright-core/index.mjs';

const root = path.dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch({
  executablePath: '/Users/kolengri/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell',
  args: ['--use-angle=metal'],
});
try {
  const page = await browser.newPage({ viewport: { width: 728, height: 900 } });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(pathToFileURL(path.join(root, 'viewer.html')).href);
  const clips = ['5965', '5915', '5887', '0001', '9066'];
  const results = [];
  for (const [index, id] of clips.entries()) {
    await page.locator('nav button').nth(index).click();
    await page.waitForFunction(() => document.querySelector('video').readyState >= 2);
    const result = await page.evaluate(() => {
      const video = document.querySelector('video');
      const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
      const context=canvas.getContext('2d');context.drawImage(video,0,0);
      return { id: window.selectedClip, width: video.videoWidth, height: video.videoHeight,
        cornerAlpha:context.getImageData(0,0,1,1).data[3],
        duration: video.duration, muted: video.muted, loop: video.loop,
        pressed: document.querySelectorAll('button[aria-pressed=true]').length };
    });
    assert.equal(result.id, id);
    assert.equal(result.width,640);
    assert.equal(result.height,320);
    assert.equal(result.cornerAlpha,0);
    assert.ok(Math.abs(result.duration - (id === '9066' ? 6.4 : 4)) < 0.08);
    assert.ok(result.muted && result.loop && result.pressed === 1);
    results.push(result);
  }
  await page.locator('#background').selectOption('dark');
  assert.equal(await page.locator('.stage').evaluate(e=>getComputedStyle(e).backgroundColor),'rgb(16, 25, 37)');
  await page.setViewportSize({ width: 360, height: 900 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  assert.equal(overflow, false);
  assert.deepEqual(errors, []);
  const report = { passed: true, clips: results, mobileOverflow: overflow, errors };
  fs.writeFileSync(path.join(root, 'review-page-verification.json'), JSON.stringify(report, null, 2) + '\n');
  console.log(JSON.stringify(report));
} finally {
  await browser.close();
}
