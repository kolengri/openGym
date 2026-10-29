import {readFile} from 'node:fs/promises';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url), ids = ['6033', '4348', '3244', '1906', '1777'];
const read = async file => JSON.parse(await readFile(file));
const clips = [], cameras = {}, assetFiles = {}, inputFiles = [];
for (const id of ids) {
 const directory = new URL(`assets/${id}/`, root);
 clips.push({...await read(new URL('clip.json', directory)), asset: id});
 cameras[id] = await read(new URL('cameras.json', directory));
 assetFiles[id] = new URL('motion.glb', directory);
 inputFiles.push(new URL('clip.json', directory), new URL('cameras.json', directory));
}
await buildReview({root, batch: '003', ids, clips, cameras, assetFiles, inputFiles,
 presentation: await read(new URL('presentation.json', root)), initialExerciseId: '6033'});
