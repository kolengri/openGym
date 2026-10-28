// DOM-free behavior check of the exact JavaScript and payload embedded in index.html.
// This verifies navigation/search logic; it does not claim a real-browser visual review.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('.', import.meta.url));
const html = fs.readFileSync(`${root}index.html`, 'utf8');
const payload = html.match(/<script id="data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const code = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const elements = new Map();
function element(id) {
  if (!elements.has(id)) elements.set(id, {
    textContent: id === 'data' ? payload : '', innerHTML: '', value: '',
    addEventListener() {}, querySelectorAll() { return []; },
  });
  return elements.get(id);
}
const context = vm.createContext({
  document: { getElementById: element },
  window: { addEventListener() {} },
  location: { hash: '' },
});
vm.runInContext(code, context);
assert.match(element('detail').innerHTML, /5965 — 1 2 stick drill/);
assert.match(element('detail').innerHTML, /movement_pattern_unspecified/);
assert.match(element('list').innerHTML, /href="#5965"/);
assert.match(element('summary').textContent, /6,554/);
vm.runInContext("query.value='0002';filter();location.hash='#0002';select();", context);
assert.match(element('detail').innerHTML, /prop_text_conflict/);
const detailPath = vm.runInContext("byId.get('0002').detail_page.split('#')[0]", context);
assert.match(fs.readFileSync(`${root}${detailPath}`, 'utf8'), /Do not add the bench/);
vm.runInContext("location.hash='#0004';select();", context);
assert.match(element('detail').innerHTML, /Alias 0004 resolves to canonical 5266/);
vm.runInContext("query.value='';status.value='equipment_free';filter();", context);
assert.doesNotMatch(element('list').innerHTML, /href="#4209"/);
assert.match(element('list').innerHTML, /href="#5915"/);
vm.runInContext("query.value='';status.value='';page=1;filter(false);", context);
assert.match(element('count').textContent, /Page 2/);
vm.runInContext("status.value='proposal_ready_for_review';filter();", context);
assert.doesNotMatch(element('list').innerHTML, /href="#5965"/);
vm.runInContext("location.hash='#not-a-real-id';select();", context);
assert.match(element('detail').innerHTML, /No matching exercise ID/);
assert.equal(vm.runInContext("esc('<img onerror=bad>')", context), '&lt;img onerror=bad&gt;');
const result = {
  passed: true,
  checks: ['Embedded JavaScript executed', 'First sample and source gap rendered',
    'Bench conflict rendered', 'Alias navigation resolved', 'Equipment-free filter excluded box jump',
    'Pagination and separate storyboard readiness filter', 'Unknown ID handled', 'Source content escaped'],
  real_browser_visual_review: false,
};
fs.writeFileSync(`${root}index-verification.json`, `${JSON.stringify(result, null, 2)}\n`);
process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
