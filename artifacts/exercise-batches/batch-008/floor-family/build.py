"""Bake source-safe actions, assert saved matrices and render early native proofs."""
import hashlib,json,sys,math
from pathlib import Path
import bpy,numpy as np
from mathutils import Vector
F=Path(__file__).resolve().parent
ID=sys.argv[sys.argv.index('--')+1]
P=F.parent/'assets'/ID;P.mkdir(exist_ok=True,parents=True)
sys.path[:0]=[str(F),str(F.parent.parent/'batch-007/prone-family'),str(F.parent.parent/'batch-003')]
import authoring as a,motion
original=a.initialize();body,rig,scene=a.body,a.rig,a.scene
for m in body.modifiers:
    m.show_viewport=m.show_render=m.type=='ARMATURE'
    if m.type=='ARMATURE':m.use_deform_preserve_volume=True
sys.path.insert(0,str(F.parent.parent/'batch-006/upright-cardio-family'))
import binding
receipt=binding.apply(body)
motion.configure(a)
receipt['original_binding_sha256']=original
receipt['runtime_binding_sha256']=a.binding_hash(body,rig)
(P/'local-binding-report.json').write_text(json.dumps(receipt,indent=2)+'\n')
rest=np.array([v.co[:]for v in body.data.vertices]);names={g.index:g.name for g in body.vertex_groups}
pelvis=np.array([8650,8586,8652,8590,3392,3329,3394,3333]) if ID=='3204' else np.where((rest[:,2]>.86)&(rest[:,2]<1.03)&(abs(rest[:,0])<.18))[0]
patches={}
for side,sign in [('Left',1),('Right',-1)]:
    patches[side+'_foot']=np.array([v.index for v in body.data.vertices if v.co.z<.035 and sign*v.co.x>.10],int)
    patches[side+'_hand']=np.array([v.index for v in body.data.vertices if sum(g.weight for g in v.groups if names[g.group].startswith(side)and any(x in names[g.group]for x in ['Hand','Index','Middle','Ring','Little','Thumb']))>.5],int)
def points():
    bpy.context.view_layer.update();ev=body.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();p=np.array([v.co[:]for v in me.vertices]);ev.to_mesh_clear();return p
offset={};root=.108 if ID=='3204'else .15
motion.pose(a,0,ID,root);p=points();root+=.001-float(p[pelvis,2].min())
motion.pose(a,0,ID,root);p=points()
for k,idx in patches.items():
    if k.endswith('_hand') and ID!='3204':offset[k]=.001-float(p[idx,2].min())
    elif k.endswith('_foot') and ID=='3204':offset[k]=.001-float(p[idx,2].min())
if ID!='3204':
    # Wrist height also changes the source-derived palm frame. Solve the
    # actual skin residual, rather than treating that coupled offset as linear.
    for _ in range(8):
        motion.pose(a,0,ID,root,offset);p=points()
        residual={k:.001-float(p[idx,2].min())for k,idx in patches.items()if k.endswith('_hand')}
        if max(abs(v)for v in residual.values())<1e-6:break
        for k,v in residual.items():offset[k]+=v
captured=[];expected={};witness=[];previous={}
for frame in range(151):
    scene.frame_set(frame+1)
    desired,state=motion.pose(a,frame,ID,root,offset);p=points()
    # Exact pelvic support follows its changing native soft-tissue contour.
    rr=root+.001-float(p[pelvis,2].min())
    desired,state=motion.pose(a,frame,ID,rr,offset);p=points()
    err=max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-np.array(m))))for n,m in desired.items());assert err<2e-6
    row={}
    for bone in rig.pose.bones:
        q=bone.rotation_quaternion.copy()
        if bone.name in previous and q.dot(previous[bone.name])<0:q.negate()
        previous[bone.name]=q.copy();row[bone.name]=(bone.location.copy(),q)
    captured.append(row);expected[frame]={n:np.array(m)for n,m in desired.items()}
    witness.append({**state,'frame':frame,'root_z_m':rr,'floor_min_z_m':float(p[:,2].min()),'pelvis_min_z_m':float(p[pelvis,2].min()),'patch_min_z_m':{k:float(p[idx,2].min())for k,idx in patches.items()}})
rig.animation_data_create();act=bpy.data.actions.new('Exercise_'+ID);act.use_fake_user=True;rig.animation_data.action=act
for frame,row in enumerate(captured):
    scene.frame_set(frame+1)
    for bone in rig.pose.bones:
        bone.location,bone.rotation_quaternion=row[bone.name];bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_quaternion',frame=frame+1)
for layer in act.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
if ID=='4935':
    copy=act.copy();copy.name='Exercise_3483';copy.use_fake_user=True
attr=body.data.attributes.get('_SOURCE_INDEX')or body.data.attributes.new('_SOURCE_INDEX','FLOAT','POINT');attr.data.foreach_set('value',np.arange(10582,dtype=np.float32))
scene.frame_start=1;scene.frame_end=151;scene.render.fps=30
scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1100;scene.render.resolution_y=650;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
shade=scene.display.shading;shade.light='STUDIO';shade.color_type='MATERIAL';shade.show_shadows=False;shade.show_cavity=False;shade.show_specular_highlight=False;scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
cd=bpy.data.cameras.new('ReviewCamera');cam=bpy.data.objects.new('ReviewCamera',cd);scene.collection.objects.link(cam);scene.camera=cam;cd.type='ORTHO'
target=[0,.05,.65]if ID=='3204'else[0,-.1,.18]
cameras=[{'label':'side_whole_body','position':[4,.05,1.0]if ID=='3204'else[4,-.1,.6],'target':target,'scale':2.65},{'label':'oblique_whole_body','position':[3,-4,3.2],'target':target,'scale':2.8}]
(P/'cameras.json').write_text(json.dumps(cameras,indent=2)+'\n');scene.frame_set(1);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(P/'source.blend'))
bpy.ops.wm.open_mainfile(filepath=str(P/'source.blend'));body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene;cam=scene.camera
saved_error=0
for frame in range(151):
    scene.frame_set(frame+1);bpy.context.view_layer.update();saved_error=max(saved_error,max(float(np.max(abs(np.array(rig.pose.bones[n].matrix)-m)))for n,m in expected[frame].items()))
assert saved_error<2e-6
proofs=[]
proof_frames=[(0,'start'),(30,'curl'),(72,'peak'),(120,'lower'),(150,'return')]if ID=='3204'else[(0,'start'),(24,'lift'),(48,'sweep'),(72,'hips'),(120,'overhead-return'),(150,'return')]
for f,label in proof_frames:
    scene.frame_set(f+1)
    for v in cameras:
        cam.location=v['position'];cam.rotation_euler=(Vector(v['target'])-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=v['scale'];before=points();scene.render.filepath=str(P/f'early-{label}-{v["label"]}.png');bpy.ops.render.render(write_still=True);after=points();assert np.array_equal(before,after)
        proofs.append({'frame':f,'view':v['label'],'file':Path(scene.render.filepath).name,'pre_post_render_skin_delta_m':0})
(P/'early-proof-readback.json').write_text(json.dumps({'actual_saved_matrix_max_error':saved_error,'contact_offsets_m':offset,'proofs':proofs,'witness':witness},indent=2)+'\n')
print('EARLY_READY',ID,'minfloor',min(x['floor_min_z_m']for x in witness),'savederror',saved_error,flush=True)
