import {readFile, writeFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = new URL('./', import.meta.url);
const sourceFile = new URL('../../bodyweight-five/runtime-muscles.json', import.meta.url);
const softFile = new URL('../batch-005/soft-abdominal-regions.json', import.meta.url);
const sourceBytes = await readFile(sourceFile), softBytes = await readFile(softFile);
const atlas = JSON.parse(sourceBytes), soft = JSON.parse(softBytes);
if (atlas.source_vertices !== soft.sourceVertices) throw Error('Abdominal field source domain mismatch');
for (const [name, region] of Object.entries(soft.regions)) {
 if (!atlas.regions[name]) throw Error('Unknown source muscle region: ' + name);
 atlas.regions[name] = region;
}
await writeFile(new URL('muscle-atlas.json', root), JSON.stringify(atlas) + '\n');
await writeFile(new URL('muscle-atlas-provenance.json', root), JSON.stringify({
 sourceVertices: atlas.source_vertices,
 sourceAtlasSha256: createHash('sha256').update(sourceBytes).digest('hex'),
 softenedAbdominalFieldsSha256: createHash('sha256').update(softBytes).digest('hex'),
 method: 'Reuse the accepted source-label atlas and exactly the batch005 neutral-graph softened abdominal regions. One shared atlas is emitted for this source domain, avoiding duplicate per-exercise field payloads.',
 geometryChanged: false, sourceLabelsChanged: false,
 sourceBodyInvariant: 'All batch006 assets must retain the canonical CC0 Basis and source IDs. The runtime builder validates each model domain.'
}, null, 2) + '\n');
