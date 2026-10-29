import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url);
const selectionFile = new URL('selection.json', root);
const ids = JSON.parse(await readFile(selectionFile)).exercise_ids;
const read = async file => JSON.parse(await readFile(file));
const clips = [], cameras = {}, assetFiles = {}, inputFiles = [], atlasOverrides = {};
const sharedModels = new Map();
const displayRoles = {'4436': {primary: ['quadriceps', 'glutes'], secondary: ['calves', 'core']}};
const phaseFile = new URL('phase-labels.json', root), phaseLabels = await read(phaseFile);
inputFiles.push(phaseFile, selectionFile);
for (const id of ids) {
 const directory = new URL(`assets/${id}/`, root);
 const metadata = await read(new URL('clip.json', directory));
 const modelFile = new URL('motion.glb', directory);
 const modelHash = createHash('sha256').update(await readFile(modelFile)).digest('hex');
 const asset = sharedModels.get(modelHash) ?? metadata.asset ?? id;
 sharedModels.set(modelHash, asset);
 const clip = {...metadata, asset, allow_unmapped_secondary: id === '1368', primary: metadata.display_primary ?? displayRoles[id]?.primary ?? metadata.primary,
  secondary: metadata.display_secondary ?? displayRoles[id]?.secondary ?? metadata.secondary,
  phases: metadata.phases.map(phase => ({...phase, label: phaseLabels[phase.label] ?? phase.label}))};
 clips.push(clip);
 if (clip.heat_regions_file) {
  const file = new URL(clip.heat_regions_file, directory);
  atlasOverrides[id] = await read(file); inputFiles.push(file);
 }
 cameras[id] = await read(new URL('cameras.json', directory));
 assetFiles[asset] ??= modelFile;
 inputFiles.push(new URL('clip.json', directory), new URL('cameras.json', directory));
}
await buildReview({root, batch: '007', ids, clips, cameras, assetFiles, inputFiles, atlasOverrides,
 atlasFile: new URL('muscle-atlas.json', root),
 presentation: await read(new URL('presentation.json', root)), initialExerciseId: '4437'});
