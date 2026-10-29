"""Render first-five actions using the prepared anatomical texture atlas."""
import bpy,sys,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
proof_only='--proof-only' in args
only_id=args[args.index('--exercise')+1] if '--exercise' in args else None
previous_receipt=args[args.index('--previous-receipt')+1] if '--previous-receipt' in args else None
sys.path.insert(0,str(P));from shot_plan import SHOTS
bpy.ops.wm.open_mainfile(filepath=str(P/'bodyweight-five.blend'))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
sys.path.insert(0,str(P.parent/'mannequin-muscle-atlas'));import muscle_atlas as atlas
atlas.prepare(body);atlas.prepare_texture(body)
# Masks are cached in NumPy for this render; avoid subdividing 96 unused point fields.
for attribute in list(body.data.attributes):
    if attribute.name.startswith(atlas.WEIGHT_PREFIX):body.data.attributes.remove(attribute)
scene.display.shading.color_type='TEXTURE';scene.display.shading.show_shadows=False
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.curvature_ridge_factor=1.35;scene.display.shading.curvature_valley_factor=1.15
from lighting import configure
lighting_report=configure(scene)
scene.render.resolution_x=768;scene.render.resolution_y=768;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.color_mode='RGBA'
items=json.loads((P/'clips.json').read_text());reports=[]
if only_id and only_id not in {item['id'] for item in items}:raise ValueError('Unknown clip: '+only_id)
def camera(item,view=None):
    plan=SHOTS[item['id']][1 if view=='detail' else 0]
    target=Vector(plan['target']);scene.camera.location=plan['position'];scale=plan['scale']
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler();scene.camera.data.ortho_scale=scale
for item in items:
    identifier=item['id'];rig.animation_data.action=bpy.data.actions[item['action']]
    def selected(names):
        regions=[]
        for name in names:
            sides=item.get('highlight_sides',{}).get(name)
            regions.extend(region for region in atlas.resolve_names([name],strict=True)['regions']
                           if sides is None or region.rsplit('.',1)[-1] in sides)
        return regions
    report=atlas.apply(body,selected(item['primary']),selected(item['secondary']),1.,stretch_names=selected(item['stretch']),strict=True)
    atlas.export_texture(body,str(P/f'texture-{identifier}.png'),pack=False)
    n=item['frames'];scene.frame_start=1;scene.frame_end=n+1
    views=['main','detail']
    for view in views if not only_id or identifier==only_id else []:
        camera(item,view);out=P/('frames-'+identifier+('-'+view if view!='main' else ''));out.mkdir(exist_ok=True)
        indices=sorted({0,n//4,n//2,3*n//4}) if proof_only else range(n)
        for i in indices:
            scene.frame_set(i+1);scene.render.filepath=str(out/f'{i:04d}.png');bpy.ops.render.render(write_still=True)
            if i in {0,n//4,n//2,3*n//4}:
                bpy.data.images['Render Result'].save_render(str(P/f'colored-{identifier}-{view}-{i:03d}.png'))
    reports.append({'id':identifier,'frames':n,'atlas':report,'views':SHOTS[identifier],
        'rendered_this_run':not only_id or identifier==only_id})
atlas.apply(body,[],[],0.);atlas.export_texture(body,str(P/'texture-neutral.png'),pack=True)
rig.animation_data.action=bpy.data.actions[items[0]['action']];camera(items[0]);scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'bodyweight-five-highlight.blend'))
result={'proof_only':proof_only,'width':768,'height':768,'fps':30,'transparent':True,'inactive_anatomy':False,'renderer':'Blender Workbench / continuous 3D texture surface','lighting':lighting_report,'clips':reports}
if only_id:result.update({'rendered_ids':[only_id],'retained_ids':[item['id'] for item in items if item['id']!=only_id],
    'previous_receipt':previous_receipt})
(P/'render-report.json').write_text(json.dumps(result,indent=2)+'\n')
print('Rendered',sum(item['rendered_this_run'] for item in reports),'exercise actions')
