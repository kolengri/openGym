import {readFile} from 'node:fs/promises';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url), ids = ['1980', '2098', '1977', '4512', '0003'];
const read = async file => JSON.parse(await readFile(file));
const clips = [], cameras = {}, assetFiles = {}, inputFiles = [], atlasOverrides = {};
for (const id of ids) {
 const directory = new URL(`assets/${id}/`, root);
 const clip = {...await read(new URL('clip.json', directory)), asset: id};
 clips.push(clip);
 if (clip.heat_regions_file) {
  const file = new URL(clip.heat_regions_file, directory);
  atlasOverrides[id] = await read(file); inputFiles.push(file);
 }
 cameras[id] = await read(new URL('cameras.json', directory));
 assetFiles[id] = new URL('motion.glb', directory);
 inputFiles.push(new URL('clip.json', directory), new URL('cameras.json', directory));
}
await buildReview({root, batch: '004', ids, clips, cameras, assetFiles, inputFiles, atlasOverrides,
 presentation: await read(new URL('presentation.json', root)), initialExerciseId: '1980'});
