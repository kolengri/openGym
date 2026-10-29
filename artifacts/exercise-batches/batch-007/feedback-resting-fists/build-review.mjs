import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = new URL('./', import.meta.url);
const inline = await readFile(new URL('../inline.html', root), 'utf8');
const capture = JSON.parse(await readFile(new URL('capture.json', root)));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const assets = [];
async function figure(file, caption) {
 const entry = capture.evidence.find(item => item.file === file);
 if (!entry) throw Error('Missing captured proof: ' + file);
 const bytes = await readFile(new URL(file, root));
 if (hash(bytes) !== entry.png_sha256) throw Error('Captured proof changed: ' + file);
 assets.push({file, sha256: hash(bytes), model: entry.model});
 return `<figure><img src="data:image/png;base64,${bytes.toString('base64')}" alt="${caption}"><figcaption>${caption}</figcaption></figure>`;
}
const gallery = `<section class="feedback-gallery" aria-label="Кулаки крупным планом">
 <h2>Кисти: до и после</h2>
 <p>Один ракурс и момент движения. Пальцы собраны к ладони, большой палец снаружи.</p>
 <div class="feedback-pair">${await figure('007-4437-hand-palmar-before.png', 'До')}${await figure('007-4437-hand-palmar-after.png', 'После')}</div>
 <div class="feedback-pair">${await figure('007-4437-hand-profile-after.png', 'После · сгиб пальцев сбоку')}</div>
 <p>То же исправление кистей применяется к ударам из предыдущей группы.</p>
</section>`;
const css = `<style>.feedback-gallery{margin-top:24px}.feedback-gallery h2{margin-bottom:4px}.feedback-pair{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.feedback-pair figure{margin:0}.feedback-pair img{display:block;width:100%;height:auto;border-radius:var(--radius,10px)}.feedback-pair figcaption{padding:5px 0;color:var(--muted-foreground)}@media(max-width:520px){.feedback-pair{grid-template-columns:1fr}}</style>`;
const html = inline.replace('</head>', css + '</head>').replace('</body>', gallery + '</body>');
if (Buffer.byteLength(html) >= 512000) throw Error('Inline comparison exceeds the host limit');
await writeFile(new URL('review.html', root), html);
await writeFile(new URL('review-build.json', root), JSON.stringify({
 scope: 'Exact pinned live batch007 inline review plus unchanged selected actual GPU before/after PNGs.',
 inline_sha256: hash(inline), review_sha256: hash(html), review_bytes: Buffer.byteLength(html), assets,
}, null, 2) + '\n');
console.log(JSON.stringify({bytes: Buffer.byteLength(html), sha256: hash(html)}));
