import {readFile} from 'node:fs/promises';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url), ids = ['1512', '3479', '0006', '4918', '4826', '4001', '3590', '4354', '3531', '3480', '5106'];
const read = async file => JSON.parse(await readFile(file));
const clips = [], cameras = {}, assetFiles = {}, inputFiles = [], atlasOverrides = {};
const phaseFile = new URL('phase-labels.json', root), phaseLabels = await read(phaseFile);
inputFiles.push(phaseFile);
for (const id of ids) {
 const directory = new URL(`assets/${id}/`, root);
 const metadata = await read(new URL('clip.json', directory));
 const asset = metadata.asset ?? id;
 const clip = {...metadata, asset, primary: metadata.display_primary ?? metadata.primary,
  secondary: metadata.display_secondary ?? metadata.secondary,
  phases: metadata.phases.map(phase => ({...phase, label: phaseLabels[phase.label] ?? phase.label}))};
 clips.push(clip);
 if (clip.heat_regions_file) {
  const file = new URL(clip.heat_regions_file, directory);
  atlasOverrides[id] = await read(file); inputFiles.push(file);
 }
 cameras[id] = await read(new URL('cameras.json', directory));
 assetFiles[asset] ??= new URL('motion.glb', directory);
 inputFiles.push(new URL('clip.json', directory), new URL('cameras.json', directory));
}
await buildReview({root, batch: '006', ids, clips, cameras, assetFiles, inputFiles, atlasOverrides,
 atlasFile: new URL('muscle-atlas.json', root),
 presentation: await read(new URL('presentation.json', root)), initialExerciseId: '1512'});
