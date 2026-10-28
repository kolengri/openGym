"""Check delivered rig poses, floor contacts, loop seams and skin topology."""
import bpy,json,sys,math,argparse,hashlib
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser();parser.add_argument('--exercise',nargs='+');parser.add_argument('--output-dir',type=Path,default=P);parser.add_argument('--source',type=Path,default=P/'bodyweight-five.blend');options=parser.parse_args(args)
bpy.ops.wm.open_mainfile(filepath=str(options.source))
body=bpy.data.objects['SK_BlenderStudioHuman'];rig=bpy.data.objects['RIG_BlenderStudioHuman'];scene=bpy.context.scene
clips=json.loads((P/'clips.json').read_text());reports=[];samples=[]
if options.exercise:clips=[item for item in clips if item['id'] in options.exercise]
if not clips:raise ValueError('No selected exercise clips')
options.output_dir.mkdir(parents=True,exist_ok=True)
for item in clips:
    rig.animation_data.action=bpy.data.actions[item['action']];n=item['frames'];poses=[];positions={}
    indices=sorted({0,n//4,n//2,3*n//4,n}|({2,10,17,21} if item['id']=='9066' else set()))
    for index in indices:
        scene.frame_set(index+1);bpy.context.view_layer.update()
        joints={pb.name:list((rig.matrix_world@pb.matrix).translation) for pb in rig.pose.bones}
        if index in [0,n]:positions[index]=joints
        evaluated=body.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
        co=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',co);co=co.reshape(-1,3)
        contacts={}
        for side in ['Left','Right']:
            for part in ['Foot','Hand']:
                names={side+'Foot',side+'ToeBase'} if part=='Foot' else {side+'Hand'}|{b.name for b in rig.data.bones if b.name.startswith(side) and any(f in b.name for f in ['Thumb','Index','Middle','Ring','Little'])}
                groupids={body.vertex_groups[name].index for name in names}
                ids=[v.index for v in mesh.vertices if sum(g.weight for g in v.groups if g.group in groupids)>.8]
                contacts[side+part]={'min_z':float(co[ids,2].min()),'max_z':float(co[ids,2].max())}
        poses.append({'frame':index,'body_min_z':float(co[:,2].min()),'contacts':contacts})
        samples.append({'id':item['id'],'frame':index,'joints':joints})
        evaluated.to_mesh_clear()
    loop=max((np.array(positions[0][name])-positions[n][name]).dot(np.array(positions[0][name])-positions[n][name])**.5 for name in positions[0])
    assert loop<.0001,(item['id'],'loop',loop)
    entry={'id':item['id'],'loop_max_joint_translation_error_m':float(loop),'poses':poses}
    if item['id']=='0001':
        import inspect_situp_contacts
        contact_report=inspect_situp_contacts.measure(body,rig,scene)
        (options.output_dir/'contact-report.json').write_text(json.dumps(contact_report,indent=2)+'\n')
        assert contact_report['checks_pass'],contact_report['failures']
        entry['authored_surface_contact_checks']={'pass':True,'paths':['native','linear_cage'],'samples':len(contact_report['samples']),'landmarks':'situp-repair/landmarks.json','issues_closed':False}
    if item['id']=='5915':
        scene.frame_set(n//2+1);bpy.context.view_layer.update()
        arm={}
        for side in ['Left','Right']:
            elbow=rig.pose.bones[side+'ForeArm'].head;wrist=rig.pose.bones[side+'Hand'].head
            arm[side]={'elbow_height':elbow.z,'wrist_height':wrist.z,'forearm_horizontal_offset':math.hypot(elbow.x-wrist.x,elbow.y-wrist.y)}
            assert elbow.z>wrist.z+.15,(side,'elbow too low',arm[side])
            assert arm[side]['forearm_horizontal_offset']<.055,(side,'forearm not vertical',arm[side])
        entry['chaturanga_bottom_forearms']=arm
    if item['id']=='9066':
        by_frame={sample['frame']:sample for sample in samples if sample['id']=='9066'}
        def knee_angle(index):
            joints=by_frame[index]['joints'];hip=np.array(joints['LeftUpLeg']);knee=np.array(joints['LeftLeg']);ankle=np.array(joints['LeftFoot'])
            a=hip-knee;b=ankle-knee
            return math.degrees(math.acos(np.clip(a.dot(b)/np.linalg.norm(a)/np.linalg.norm(b),-1,1)))
        loaded=knee_angle(0);flight=knee_angle(10)
        assert loaded<155,('Hop needs a visible knee bend',loaded)
        assert next(p for p in poses if p['frame']==10)['contacts']['LeftFoot']['min_z']>.10,'Hop foot must clear ground'
        assert poses[0]['contacts']['LeftFoot']['min_z']<.012,'Loaded hop must touch floor'
        entry['hop_knee_degrees']={'loaded':loaded,'flight':flight}
    assert min(p['body_min_z'] for p in poses)>-.018,(item['id'],'floor penetration',poses)
    reports.append(entry)
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-asset-qa/scripts'));import qa_check
scene.frame_set(1)
qa=qa_check.run(objects=[body.name],profile='game')
assert qa['pass'],qa
if any(item['id']=='0001' for item in clips):
    qa_action=rig.animation_data.action
    if qa_action.name!='Exercise_0001':
        rig.animation_data.action=bpy.data.actions['Exercise_0001'];scene.frame_set(1);bpy.context.view_layer.update()
        situp_native_qa=qa_check.run(objects=[body.name],profile='game')
        assert situp_native_qa['pass'],situp_native_qa
        qa['situp_native']=situp_native_qa
    modifier_visibility=[(modifier,modifier.show_viewport) for modifier in body.modifiers]
    try:
        for modifier,_ in modifier_visibility:modifier.show_viewport=modifier.type=='ARMATURE'
        bpy.context.view_layer.update()
        linear_qa=qa_check.run(objects=[body.name],profile='game')
        assert linear_qa['pass'],linear_qa
        qa['linear_cage']=linear_qa
    finally:
        for modifier,visible in modifier_visibility:modifier.show_viewport=visible
        rig.animation_data.action=qa_action
        bpy.context.view_layer.update()
(options.output_dir/'asset-qa.json').write_text(json.dumps(qa,indent=2)+'\n')
(options.output_dir/'pose-samples.json').write_text(json.dumps(samples,indent=2)+'\n')
(options.output_dir/'pose-verification.json').write_text(json.dumps({'ok':True,'source_blend_sha256':hashlib.sha256(options.source.read_bytes()).hexdigest(),'scope':'Selected sampled poses, evaluated skin floor bounds and exact loop joint closure; 0001 additionally checks authored pelvic/heel/sole/head/hand surface patches on native and linear skin. Not a coaching/biomechanical certification or issue closure.','clips':reports},indent=2)+'\n')
print('Verified selected clip floor bounds, joint loops and exercise-specific contact checks:',','.join(item['id'] for item in clips))
