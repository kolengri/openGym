"""Prepare and validate the atlas, write a reviewable .blend, render six views."""
import bpy,sys,json,time,hashlib
from pathlib import Path
import numpy as np
from mathutils import Vector
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P));import muscle_atlas as atlas
# The canonical catalogue, rather than its legacy packed frontend subset, owns
# coverage. Regenerate the receipt every build so new spellings cannot be missed.
names={};canonical_count=0;alias_count=0
for path in sorted((P.parent.parent/'catalogue'/'exercises').glob('*.json')):
 d=json.loads(path.read_text())
 if 'target' not in d:
  if 'variantOf' in d:alias_count+=1
  continue
 canonical_count+=1
 for field,values in [('target',d['target']),('secondaryMuscles',d['secondaryMuscles']),('muscleMap.primaries',d.get('muscleMap',{}).get('primaries',[])),('muscleMap.secondaries',d.get('muscleMap',{}).get('secondaries',[]))]:
  if isinstance(values,str):values=[values]
  for name in values:
   entry=names.setdefault(name,{'fields':[],'count':0});entry['count']+=1
   if field not in entry['fields']:entry['fields'].append(field)
source={'canonical_exercise_count':canonical_count,'alias_stub_count':alias_count,'canonical_source':'catalogue/exercises/*.json','source_fields':['target','secondaryMuscles','muscleMap.primaries','muscleMap.secondaries'],'names':dict(sorted(names.items()))}
(P/'catalogue-strings.json').write_text(json.dumps(source,indent=2))
body=bpy.data.objects['SK_BlenderStudioHuman'];scene=bpy.context.scene
before=atlas._fingerprint(body);start=time.perf_counter()
weights=atlas.prepare(body,force=True)
meta=atlas.region_metadata(body)
groups={}
for k,m in meta.items():groups.setdefault(m['group'],[]).append(k)
def starts(*names):return [k for k in meta if any(k.split('.')[0].startswith(n) for n in names)]
def group(*names):return [k for n in names for k in groups[n]]
rows={}
def row(names,regions,status='surface',reason='Illustrative visible superficial surface regions.'):
 for n in names.split('|'):rows[n]={'status':status,'regions':regions,'reason':reason}
row('pectorals|chest',group('chest'))
row('upper chest',starts('pectoralis_clavicular'))
row('delts|deltoids|shoulders',group('deltoids'))
row('rear deltoids',starts('deltoid_posterior'))
row('biceps',starts('biceps'))
row('brachialis',starts('brachialis_visible'),'partial_surface','Only the lateral visible strip is shown; the remaining brachialis lies deep to biceps.')
row('triceps',group('triceps'))
row('forearm|forearms|grip muscles|wrists',group('forearm'),'group_proxy','Forearm compartment proxy; hand intrinsic muscles and wrist joints are not painted.')
row('wrist flexors',starts('forearm_flexors'))
row('wrist extensors',starts('forearm_extensors'))
row('abs|abdominals',group('abs'))
row('core',group('abs','obliques','lower-back'),'group_proxy','Broad training term; superficial abdominal wall and erector columns proxy the group, not all deep stabilizers.')
row('lower abs',starts('rectus_abdominis_3','rectus_abdominis_4'),'group_proxy','Inferior display blocks of the same rectus abdominis, not separate muscles.')
row('obliques',group('obliques'))
row('serratus|serratus anterior',group('serratus'),'partial_surface','Visible anterolateral slips only; not the portion deep to the scapula.')
row('lats|latissimus dorsi',starts('latissimus_dorsi'))
row('traps|trapezius',group('trapezius'))
row('upper back|upper-back|back',group('upper-back','trapezius'),'group_proxy','Training group combines lats, trapezius and visible posterior scapular regions; deep rhomboids are omitted unless requested explicitly.')
# Exclude deep projection from general upper back so the surface ordering is unambiguous.
for n in ['upper back','upper-back','back']:rows[n]['regions']=[k for k in rows[n]['regions'] if meta[k]['visibility']!='deep_projection']
row('rhomboids',starts('rhomboid_projection'),'deep_projection','Rhomboids are deep to trapezius; this is an overlaid surface projection, not exposed rhomboid tissue.')
row('rotator cuff',starts('infraspinatus'),'deep_projection','Only a posterior infraspinatus area proxy is visible; supraspinatus, subscapularis and deep cuff tendons are not claimed as surface segmentation.')
row('levator scapulae',starts('trapezius_upper'),'deep_projection','Approximate upper trapezius surface proxy over the deep levator scapulae; the muscles are not equivalent.')
row('lower back|lower-back|spine',group('lower-back'),'group_proxy','Erector spinae surface columns proxy lower back; spine denotes a training target, not muscle tissue.')
row('glutes|gluteal',group('gluteal'))
row('abductors',starts('gluteus_medius_visible','tensor_fasciae_latae'),'group_proxy','Visible gluteus medius and tensor fasciae latae; deep gluteus minimus is omitted.')
row('quads|quadriceps',group('quadriceps'),'partial_surface','Rectus femoris, vastus medialis and lateralis are visible; deep vastus intermedius is intentionally omitted.')
row('hamstring|hamstrings',group('hamstring'))
row('adductors|groin|inner thighs',group('adductors'),'partial_surface','Visible medial thigh/adductor regions; deep origins and other groin anatomy are omitted.')
row('hip flexors|hip-flexors',starts('iliopsoas_projection','sartorius'),'deep_projection','Iliopsoas is deep: a limited anterior hip projection plus visible sartorius region, not exposed iliopsoas tissue.')
row('calves',group('calves'))
row('soleus',starts('soleus_'),'partial_surface','Visible medial/lateral strips beside and below gastrocnemius; no false full superficial soleus patch.')
row('shins',group('tibialis'))
row('sternocleidomastoid',group('neck'))
row('cardiovascular system',[],'systemic','System-level exercise demand has no localized muscle surface.')
row('hands|feet|ankles|ankle stabilizers',[],'unsupported','No defensible individual intrinsic hand/foot or ankle stabilizer segmentation is authored for this mannequin.')
source=json.loads((P/'catalogue-strings.json').read_text())
assert set(source['names'])<=set(rows),sorted(set(source['names'])-set(rows))
assert all(k in weights for r in rows.values() for k in r['regions'])
region_counts={k:{**meta[k],'weighted_vertices':int((v>.01).sum()),'core_vertices':int((v>.5).sum()),'max_weight':float(v.max())} for k,v in weights.items()}
empty=[k for k,v in weights.items() if not np.any(v>.1)]
assert not empty,empty
mapping={'$schema':'./region-map.schema.json','version':atlas.VERSION,'notice':'Illustrative artist-authored masks on an original CC0 mesh. Not anatomical segmentation, EMG, physiological activation, or medical guidance.','body':{'name':body.name,'source':'Blender Studio Human Base Meshes v1.4.1 / realistic male / CC0','base_vertices':len(body.data.vertices),'base_polygons':len(body.data.polygons),'units':'m','height':1.8,'front':'-Y','left':'+X','rest_sha256':before},'catalogue':{'canonical_records':source['canonical_exercise_count'],'distinct_names':len(source['names']),'alias_stubs':source['alias_stub_count'],'fields':source['source_fields']},'regions':region_counts,'mappings':rows,'sources':[{'title':'OpenStax Anatomy and Physiology 2e, 11.4','url':'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-4-axial-muscles-of-the-abdominal-wall-and-thorax','use':'Abdominal layer ordering and rectus/oblique arrangement.'},{'title':'OpenStax Anatomy and Physiology 2e, 11.5','url':'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-5-muscles-of-the-pectoral-girdle-and-upper-limbs','use':'Chest/shoulder/upper limb superficial shape, back muscle layering and cuff limitations.'},{'title':'OpenStax Anatomy and Physiology 2e, 11.6','url':'https://openstax.org/books/anatomy-and-physiology-2e/pages/11-6-appendicular-muscles-of-the-pelvic-girdle-and-lower-limbs','use':'Pelvic/thigh/leg compartments and deep vs visible regions.'}]}
(P/'region-map.json').write_text(json.dumps(mapping,indent=2))
atlas.prepare_texture(body)
# Keep the imported source cage untouched. The only geometry remains the source.
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
sh=scene.display.shading;sh.light='STUDIO';sh.studiolight_rotate_z=.35;sh.color_type='TEXTURE';sh.show_shadows=True;sh.show_cavity=True;sh.cavity_type='BOTH';sh.curvature_ridge_factor=1.2;sh.curvature_valley_factor=1.05;sh.show_specular_highlight=False;sh.background_type='WORLD';scene.world.color=(.055,.065,.075)
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
from lighting import configure
lighting_report=configure(scene)
cam=scene.camera;cam.data.type='ORTHO';cam.data.ortho_scale=2.02
# Verify the requested display contract against actual vertex/image data. The
# detailed neutral drawing stays cached for the explicit optional display mode.
atlas.apply(body)
vertex_colors=np.empty((len(body.data.vertices),4),np.float32)
body.data.color_attributes[atlas.COLOR_ATTRIBUTE].data.foreach_get('color',vertex_colors.ravel())
assert np.array_equal(vertex_colors[:,:3],np.broadcast_to(atlas.NEUTRAL_COLOR,(len(vertex_colors),3)))
texture=atlas._CACHE[body.data.as_pointer()]['texture']
texture_pixels=np.empty((texture['shape'][0]*texture['shape'][1],4),np.float32)
texture['image'].pixels.foreach_get(texture_pixels.ravel())
neutral_pixel=texture_pixels[0,:3].copy()
assert np.all(texture_pixels[:,:3]==neutral_pixel)
atlas.apply(body,['biceps'],['forearms'],stretch_names=['hamstrings'])
body.data.color_attributes[atlas.COLOR_ATTRIBUTE].data.foreach_get('color',vertex_colors.ravel())
selected=atlas.resolve_names(['biceps','forearms','hamstrings'])['regions']
vertex_support=np.maximum.reduce([weights[k] for k in selected])>0
assert np.all(vertex_colors[~vertex_support,:3]==atlas.NEUTRAL_COLOR)
texel_support=np.zeros(len(texture_pixels),bool)
for k in selected:
 idx,_=texture['weights'][k];texel_support[texture['indices'][idx]]=True
texture['image'].pixels.foreach_get(texture_pixels.ravel())
assert np.all(texture_pixels[~texel_support,:3]==neutral_pixel)
fiber_indices,core_weights=texture['weights']['biceps.L']
fiber_indices=fiber_indices[core_weights>.99]
assert len(fiber_indices)>0 and np.ptp(texture['fiber'][fiber_indices])>.05
assert np.ptp(texture_pixels[texture['indices'][fiber_indices],0])>.02
atlas.apply(body,show_inactive_anatomy=True)
body.data.color_attributes[atlas.COLOR_ATTRIBUTE].data.foreach_get('color',vertex_colors.ravel())
assert np.ptp(vertex_colors[:,0])>.05
atlas.apply(body)
del texture_pixels,vertex_colors,texel_support
texture_exports=[]
atlas.apply(body);texture_exports.append(atlas.export_texture(body,P/'textures'/'neutral.png'))
roles={}
for exercise_id in ['5965','5915','5887','0001','9066']:
 d=json.loads((P.parent.parent/'catalogue'/'exercises'/f'{exercise_id}.json').read_text())
 primary=d.get('muscleMap',{}).get('primaries',[d['target']]);secondary=d.get('muscleMap',{}).get('secondaries',d['secondaryMuscles']);stretch=[]
 # Explicit role correction supplied by the primary: three-legged downward dog
 # stretches hamstrings, rather than coloring them as actively loaded primaries.
 if exercise_id=='5887':stretch=primary;primary=[]
 atlas.apply(body,primary,secondary,stretch_names=stretch)
 texture_exports.append(atlas.export_texture(body,P/'textures'/f'{exercise_id}-activation.png'))
 texture_exports.append(atlas.export_role_mask(body,P/'textures'/f'{exercise_id}-roles.png',primary,secondary,stretch_names=stretch))
 roles[exercise_id]={'name':d['name'],'primary':primary,'secondary':secondary,'stretch':stretch,'activation_texture':f'{exercise_id}-activation.png','role_mask':f'{exercise_id}-roles.png'}
(P/'textures'/'manifest.json').write_text(json.dumps({'neutral':'neutral.png','inactive_anatomy':'uniform neutral; no drawn regions, fibers or seams','activation_color_space':'sRGB','role_mask_color_space':'linear non-color','channels':{'R':'primary','G':'secondary','B':'stretch'},'priority':['primary','secondary','stretch'],'exercises':roles},indent=2))
renders=[]
for mode in ['neutral','activation']:
 if mode=='neutral':atlas.apply(body)
 else:atlas.apply(body,['pectorals','biceps','abs','quads','glutes','lats','traps'],['obliques','forearms','calves'],stretch_names=['hamstrings'])
 for view,loc in [('front',(0,-6,.93)),('side',(6,0,.93)),('back',(0,6,.93))]:
  cam.location=loc;cam.rotation_euler=(Vector((0,0,.91))-cam.location).to_track_quat('-Z','Y').to_euler()
  scene.render.filepath=str(P/f'{mode}-{view}.png');bpy.ops.render.render(write_still=True);renders.append(Path(scene.render.filepath).name)
# Persist neutral, front-view source for integration. No animation is baked.
atlas.apply(body);cam.location=(0,-6,.93);cam.rotation_euler=(Vector((0,0,.91))-cam.location).to_track_quat('-Z','Y').to_euler()
atlas._CACHE[body.data.as_pointer()]['texture']['image'].pack()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'mannequin-muscle-atlas.blend'))
# Invariants and failure behavior are proportionate to attribute-only changes.
after=atlas._fingerprint(body);assert before==after
first=np.empty(len(body.data.vertices)*4,np.float32);second=first.copy()
atlas.apply(body,['quads'],['glutes'],.6);body.data.color_attributes[atlas.COLOR_ATTRIBUTE].data.foreach_get('color',first)
atlas.apply(body,['quads'],['glutes'],.6);body.data.color_attributes[atlas.COLOR_ATTRIBUTE].data.foreach_get('color',second)
assert np.array_equal(first,second)
assert not atlas.resolve_names(source['names'],strict=True)['unknown']
try:atlas.apply(body,['__unknown__'],strict=True)
except ValueError:unknown_rejected=True
else:raise AssertionError('Unknown strict muscle string accepted')
try:atlas.apply(body,strength=float('nan'))
except ValueError:nan_rejected=True
else:raise AssertionError('NaN strength accepted')
report={'blender':bpy.app.version_string,'catalogue_records':source['canonical_exercise_count'],'distinct_names':len(source['names']),'mapped_names':len(rows),'regions':len(weights),'nonempty_regions':len(weights)-len(empty),'original_vertex_count':len(body.data.vertices),'original_face_count':len(body.data.polygons),'triangles':sum(len(p.vertices)-2 for p in body.data.polygons),'topology_and_coordinates_unchanged':before==after,'rest_sha256':before,'deterministic_colors':True,'strict_unknown_rejected':unknown_rejected,'nan_strength_rejected':nan_rejected,'no_extra_surface_meshes':len([o for o in scene.objects if o.type=='MESH'])==1,'rendered_pngs':renders,'exported_textures':[str(Path(p).relative_to(P)) for p in texture_exports],'packed_texture':True,'elapsed_seconds':round(time.perf_counter()-start,3),'claim':'Illustrative surface masks; not anatomical segmentation or EMG.'}
report.update({'all_region_weights_finite':all(np.isfinite(v).all() for v in weights.values()),'all_catalogue_names_resolve':True,'mapping_semantic_references_valid':True,'schema_validation':'JSON parsed and required keys/statuses/references checked with standard library; no third-party JSON Schema validator installed.'})
report.update({'inactive_vertex_colors_uniform':True,'inactive_texture_pixels_uniform':True,'unselected_vertex_and_texture_colors_unchanged':True,'selected_fiber_detail_retained':True,'show_inactive_anatomy_default':False,'optional_detailed_neutral_available':True,'global_shader_bump':False,'lighting':lighting_report})
(P/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
