import {readFile} from 'node:fs/promises';
import {buildReview} from '../build-review.mjs';

const root = new URL('./', import.meta.url), source = new URL('../../bodyweight-next-five/', root);
const read = async file => JSON.parse(await readFile(file));
const clips = (await read(new URL('clips.json', source))).filter(clip => !['10565', '6560'].includes(clip.id));
clips.push(...await read(new URL('ninety-clips.json', source)));
const cameras = {...await read(new URL('camera-presets.json', source)), ...await read(new URL('ninety-camera-presets.json', source))};
await buildReview({root, batch: '002', ids: ['5265', '4007', '6428', '10565', '6560'], clips,
 cameras, presentation: await read(new URL('presentation.json', root)),
 initialExerciseId: '10565', assetFiles: {
  default: new URL('next-five.glb', source),
  'ninety-repaired': new URL('ninety-repaired.glb', source),
 }, inputFiles: ['clips.json', 'camera-presets.json', 'ninety-clips.json', 'ninety-camera-presets.json'].map(file => new URL(file, source))});
