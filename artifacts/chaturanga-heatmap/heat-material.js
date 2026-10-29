import {Color, MeshStandardMaterial} from 'three';

// One opaque skin, one material, no floating overlay geometry or bloom pass.
export function createHeatMaterial() {
 const uniforms = {
  heatEnabled: {value: 1}, heatStrength: {value: 1}, heatPhase: {value: 1},
  heatAmber: {value: new Color('#f7a64b')},
  heatRed: {value: new Color('#f24720')},
  heatCore: {value: new Color('#ffe09a')},
 };
 const material = new MeshStandardMaterial({color: '#aeb8bf', roughness: 1, metalness: 0});
 material.onBeforeCompile = shader => {
  Object.assign(shader.uniforms, uniforms);
  shader.vertexShader = shader.vertexShader.replace('#include <common>',
   '#include <common>\nattribute vec2 heatZone;\nvarying vec2 vHeatZone;')
   .replace('#include <begin_vertex>', '#include <begin_vertex>\nvHeatZone = heatZone;');
  shader.fragmentShader = shader.fragmentShader.replace('#include <common>', `#include <common>
   varying vec2 vHeatZone;
   uniform float heatEnabled;
   uniform float heatStrength;
   uniform float heatPhase;
   uniform vec3 heatAmber;
   uniform vec3 heatRed;
   uniform vec3 heatCore;`)
   .replace('#include <opaque_fragment>', `
   float zone = clamp(max(vHeatZone.x, vHeatZone.y * .49) * heatPhase, 0.0, 1.0);
   float coverage = smoothstep(.055, .68, zone) * heatEnabled;
   coverage = clamp(coverage * heatStrength, 0.0, .97);
   vec3 warmth = mix(heatAmber, heatRed, smoothstep(.30, .78, zone));
   warmth = mix(warmth, heatCore, smoothstep(.79, 1.0, zone) * .85);
   float form = clamp(dot(outgoingLight, vec3(.2126, .7152, .0722)), .35, 1.0);
   outgoingLight = mix(outgoingLight, warmth * (.82 + form * .18), coverage);
   #include <opaque_fragment>`);
 };
 material.customProgramCacheKey = () => 'surface-heat-zone-v1';
 return {material, uniforms};
}
