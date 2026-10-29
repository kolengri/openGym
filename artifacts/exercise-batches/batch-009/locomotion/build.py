"""Bake the three actions, export a moving GLB, and record early neutral proofs."""
import bpy, numpy as np, json, hashlib, sys, os
from pathlib import Path
from mathutils import Vector
F=Path(__file__).resolve().parent;B=F.parent;ROOT=B.parents[2]
sys.path[:0]=[str(F),str(B.parent/'batch-003'),str(B.parent/'batch-008/standing-dynamic')]
import authoring as a, motion, plantar_binding
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert a.initialize()=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
b,r,s=a.body,a.rig,a.scene
binding=plantar_binding.apply(b);binding['runtime_binding_sha256']=a.binding_hash(b,r)
for m in b.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
soles={side:np.array([v.index for v in b.data.vertices if v.co.z<.10 and sum(g.weight for g in v.groups if b.vertex_groups[g.group].name in [side+'Foot',side+'ToeBase'])>.5],int) for side,_ in motion.SIDES}
def points():
    bpy.context.view_layer.update();e=b.evaluated_get(bpy.context.evaluated_depsgraph_get());me=e.to_mesh();p=np.array([v.co[:] for v in me.vertices]);e.to_mesh_clear();return p
r.animation_data_create();witness={};expected={}
for ID in motion.IDS:
    action=bpy.data.actions.new('Exercise_'+ID);action.use_fake_user=True;slot=None;previous={};witness[ID]=[];expected[ID]=[]
    for f in range(151):
        r.animation_data.action=None;s.frame_set(f+1);d,st=motion.pose(a,f,ID);offsets={}
        desired={side:.001+(st['flight_height'] if st['flight'] else st.get('foot_lift',0) if ID=='3672' and side==st['moving_side'] else .045*st['kick'] if ID=='6097' and side==st['moving_side'] else 0) for side in soles}
        for _ in range(3):
            p=points()
            offsets={side:offsets.get(side,0)+desired[side]-float(p[idx,2].min()) for side,idx in soles.items()}
            d,st=motion.pose(a,f,ID,offsets)
        p=points();err=max(float(np.max(abs(np.array(r.pose.bones[n].matrix)-np.array(mat)))) for n,mat in d.items());assert err<3e-6,(ID,f,err)
        expected[ID].append(np.array([pb.matrix for pb in r.pose.bones]));st.update(ground_offsets_m=offsets,whole_skin_floor_z_m=float(p[:,2].min()),sole_minimum_z_m={side:float(p[idx,2].min()) for side,idx in soles.items()},maximum_actual_bone_matrix_error=err);witness[ID].append(st)
        r.animation_data.action=action
        if slot:r.animation_data.action_slot=slot
        for pb in r.pose.bones:
            if pb.name in previous and pb.rotation_quaternion.dot(previous[pb.name])<0:pb.rotation_quaternion.negate()
            previous[pb.name]=pb.rotation_quaternion.copy();pb.keyframe_insert('location',frame=f+1);pb.keyframe_insert('rotation_quaternion',frame=f+1)
        slot=r.animation_data.action_slot
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
attr=b.data.attributes.get('_SOURCE_INDEX') or b.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
s.frame_start=1;s.frame_end=151;s.render.fps=30;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=680;s.render.resolution_y=760;s.render.resolution_percentage=100;s.render.film_transparent=True;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGBA'
sh=s.display.shading;sh.light='STUDIO';sh.color_type='MATERIAL';sh.show_cavity=False;sh.show_shadows=False;sh.show_specular_highlight=False;s.view_settings.view_transform='Standard';s.view_settings.look='None'
cd=bpy.data.cameras.new('NativeReviewCamera');cam=bpy.data.objects.new('NativeReviewCamera',cd);s.collection.objects.link(cam);s.camera=cam;cd.type='ORTHO'
views=[{'label':'front_oblique_whole_body','position':[3.4,-5,2.0],'target':[0,-.10,1.10],'scale':3.25},{'label':'side_whole_body','position':[5,-.10,1.65],'target':[0,-.10,1.10],'scale':3.25}]
r.animation_data.action=bpy.data.actions['Exercise_3220'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(F/'source.blend'))
source_sha=sha(F/'source.blend')
for ID in motion.IDS:
    P=B/'assets'/ID;r.animation_data.action=bpy.data.actions['Exercise_'+ID];r.animation_data.action_slot=r.animation_data.action.slots[0]
    error=0.
    for f,mat in enumerate(expected[ID]):
        s.frame_set(f+1);bpy.context.view_layer.update();error=max(error,float(np.max(abs(np.array([pb.matrix for pb in r.pose.bones])-mat))))
    assert error<3e-6
    path=P/'source.blend'
    if path.exists():path.unlink()
    os.link(F/'source.blend',path)
    states={'3220':[(0,'start'),(15,'squat'),(36,'airborne-spread'),(54,'soft-landing'),(75,'return')], '3672':[(0,'start'),(15,'forward-place'),(35,'right-lunge'),(60,'step-return'),(112,'left-lunge'),(150,'return')], '6097':[(0,'shoulder-height-start'),(9,'press-intermediate'),(19,'right-backkick-press'),(38,'return'),(56,'left-backkick-press'),(150,'loop-return')]}[ID]
    proofs=[];poses=[]
    for f,label in states:
        s.frame_set(f+1);bpy.context.view_layer.update();before=points();poses.append({'id':ID,'frame':f,'joints':{pb.name:list(r.matrix_world@pb.head) for pb in r.pose.bones}})
        for view in views:
            cam.location=view['position'];cam.rotation_euler=(Vector(view['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=view['scale']/(680/760);s.render.filepath=str(P/f"early-{label}-{view['label']}.png");bpy.ops.render.render(write_still=True);assert np.array_equal(before,points());proofs.append(dict(frame=f,seconds=f/30,phase=label,view=view['label'],path=Path(s.render.filepath).name))
    record=json.loads((ROOT/'catalogue/exercises'/f'{ID}.json').read_text())
    interpretation=json.loads((B/'source-resolutions.json').read_text())[ID]
    clip=dict(id=ID,action='Exercise_'+ID,duration=5,duration_seconds=5,frames=150,fps=30,primary=[record['target']],secondary=record['secondaryMuscles'],display_mode='heat',highlight_sides={},skinning='dualQuaternion',phases=[dict(start=0,end=5,label={'3220':'Two controlled squat jumps','3672':'Right and left forward lunge and return','6097':'Four alternating backward kicks with overhead press'}[ID])],interpretation=interpretation+' All ranges and timings are authored demonstration choices; no clinical or measured activation claim.',review_status='early_native_and_moving_glb_pending_root_GPU',source_sha256=source_sha)
    for name,value in [('clip.json',clip),('cameras.json',views),('pose-samples.json',poses),('local-binding-report.json',binding),('motion-witnesses.json',dict(id=ID,source_sha256=source_sha,samples=witness[ID])),('early-report.json',dict(id=ID,source_sha256=source_sha,status='Early shape and motion evidence; final151/native/decoded QA pending.',maximum_saved_151_matrix_error=error,maximum_reach_error_m=max(v for row in witness[ID] for v in row['reach_errors_m'].values()),minimum_full_cycle_skin_z_m=min(row['whole_skin_floor_z_m'] for row in witness[ID]),proofs=proofs))]:
        (P/name).write_text(json.dumps(value,indent=2)+'\n')
    (P/'authoring-context.json').write_bytes((B/'contexts'/f'{ID}.json').read_bytes())
    print('EARLY',ID,source_sha,error,min(row['whole_skin_floor_z_m'] for row in witness[ID]))
bpy.ops.object.select_all(action='DESELECT');b.select_set(True);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.gltf(filepath=str(F/'motion.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_texcoords=True,export_normals=True,export_materials='EXPORT',export_vertex_color='NONE',export_attributes=True,export_morph=False,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='ACTION',export_force_sampling=True,export_frame_range=False,export_frame_step=1,export_anim_slide_to_zero=True,export_skins=True,export_influence_nb=4,export_def_bones=True,export_leaf_bone=False,export_rest_position_armature=True,export_extras=True,export_cameras=False,export_lights=False)
for ID in motion.IDS:
    p=B/'assets'/ID/'motion.glb'
    if p.exists():p.unlink()
    os.link(F/'motion.glb',p)
print('EXPORTED_EARLY',sha(F/'motion.glb'))
