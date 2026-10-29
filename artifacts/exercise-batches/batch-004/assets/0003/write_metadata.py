"""Write source-specific metadata without changing the frozen source or GLB."""
import hashlib,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
def write():
    read=lambda name:json.loads((P/name).read_text())
    sha=lambda name:hashlib.sha256((P/name).read_bytes()).hexdigest()
    source_sha=sha('source.blend');motion_sha=sha('motion.glb')
    record=json.loads((P.parents[4]/'catalogue/exercises/0003.json').read_text())
    corrective=read('joint-corrective-report.json')
    local_pass=all((P/name).exists()and read(name).get('source_sha256')==source_sha and read(name).get(flag,False)for name,flag in [('surface-contact-report.json','ok'),('asset-qa.json','pass'),('source-verification.json','pass'),('export-verification.json','ok')])
    local_pass=local_pass and read('export-verification.json').get('sha256')==motion_sha
    witnesses=[{'time':1.25,'frame':37.5,'elbow':'RightForeArm','knee':'LeftLeg','extended_leg':'Right'},{'time':3.75,'frame':112.5,'elbow':'LeftForeArm','knee':'RightLeg','extended_leg':'Left'}]
    clip={'id':'0003','name':'air bike','action':'Exercise_0003','duration':5,'duration_seconds':5,'frames':150,'duration_frames':150,'fps':30,'skinning':'dualQuaternion','bones':51,'primary':['abs'],'secondary':['hip flexors'],'stretch':[],'display_mode':'heat','highlight_sides':{},'phases':[{'start':0,'end':1.25,'label':'Right elbow toward left knee; right leg extends'},{'start':1.25,'end':2.5,'label':'Return through raised-knee centre'},{'start':2.5,'end':3.75,'label':'Left elbow toward right knee; left leg extends'},{'start':3.75,'end':5,'label':'Return through raised-knee centre'}],'cross_pair_witnesses':witnesses,'source_hold_recommendation_seconds':None,'source_instructions':record['instructions'],'interpretation':'One controlled alternating supine bicycle crunch. Raised legs start with knees90degrees. Separate relaxed palms remain behind the head; the active elbow approaches the opposite knee while the other leg straightens. Pelvis remains supported and both feet stay airborne. The natural lumbar arch is retained. Five-second pace is authored; source specifies desired repetitions.','explicit_staging':{'hands':'Separate palms cradle the occiput with gently articulated fingers; source palm plane is measured from original geometry. No neck pull.','wrists':'35degree palm/forearm deviation is an authored staging bound, not a clinical range.','back':'Posterior pelvic skin is supported; lumbar gap is measured without claiming whole-lumbar contact.','timing':'Opposite peaks at1.25/3.75seconds; one complete5second alternating cycle.'},'source_roles':{'primary':['abs'],'secondary':['hip flexors']},'muscle_display_roles':{'abs':{'role':'main','mapping':'Superficial rectus abdominis regions'},'hip flexors':{'role':'additional','mapping':'Visible sartorius and limited deep iliopsoas surface projection; not exposed iliopsoas tissue.'}},'artistic_emphasis':'Stable soft warm main/additional zones; neutral inactive body. No phase-dependent physiological recruitment claim.','correctives':{'names':[entry['name']for entry in corrective['keys']],'position_targets':3,'normal_targets':3,'method':corrective['method'],'maximum_rest_delta_m':max(entry['total_maximum_rest_delta_m']for entry in corrective['keys']),'flank_guard_amplitudes_m':corrective['flank_guard']['amplitudes_m'],'basis_rest_uv_weights_unchanged':True,'global_corrective_smooth_enabled':False},'source_gaps':{'timing':'Desired repetitions, no speed; one5second cycle authored.','hand_detail':'Hands behind head is sourced; separate palm placement/finger curl authored.','other_joint_angles':'Only starting90degree knees are sourced; remaining angles are illustration targets, not validated clinical ranges.'},'source_record_sha256':hashlib.sha256((P.parents[4]/'catalogue/exercises/0003.json').read_bytes()).hexdigest(),'provenance':{'text':'catalogue/exercises/0003.json','body':'Original Blender Studio CC0 Human Base Mesh in artifacts/bodyweight-five/bodyweight-five.blend','restricted_media_used':False,'paid_generation_used':False},'review_status':'source_and_cpu_checks_complete_primary_runtime_review_pending'if local_pass else'early_cage_review_draft'}
    (P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
    files={name:{'bytes':(P/name).stat().st_size,'sha256':sha(name)}for name in ['source.blend','motion.glb']}
    build={'id':'0003','blender':'5.2.3 LTS','source_sha256':source_sha,'skinning':'dualQuaternion','binding_rest_uv_sha256':'227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b','original_vertices':10582,'triangles':21160,'bones':51,'actions':['Exercise_0003'],'action_slots':['OBJECT','KEY'],'materials':1,'textures':0,'shape_keys_added':3,'corrective':corrective,'files':files,'geometry_contact_cpu_qa_ok':local_pass,'native_modifiers':'Armature PreserveVolume only. Global CorrectiveSmooth and Multires disabled; optional preview uses Multires only.','shape_acceptance':'Primary approved actual early DQ cage; final actual GPU review remains primary-owned.','ready_for_review':local_pass}
    (P/'build-report.json').write_text(json.dumps(build,indent=2)+'\n')
    if local_pass:
        poses=read('pose-samples.json');initial=next(row['joints']for row in poses if row['frame']==0)
        distance=lambda left,right:math.dist(left,right)
        angle=lambda left,right:math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(left,right))/math.sqrt(sum(x*x for x in left)*sum(y*y for y in right))))))
        subtraction=lambda left,right:[x-y for x,y in zip(left,right)]
        rows=[]
        for witness in witnesses:
            joints=next(row['joints']for row in poses if row['frame']==witness['frame'])
            elbow=witness['elbow'];knee=witness['knee'];extended=witness['extended_leg'];same_knee=extended+'Leg'
            paired=distance(joints[elbow],joints[knee]);start=distance(initial[elbow],initial[knee])
            own=distance(joints[elbow],joints[same_knee]);other_elbow=('Left'if extended=='Right'else'Right')+'ForeArm'
            other=distance(joints[other_elbow],joints[knee])
            leg_angle=angle(subtraction(joints[extended+'UpLeg'],joints[same_knee]),subtraction(joints[extended+'Foot'],joints[same_knee]))
            assert paired<start and paired<own and paired<other and leg_angle>150
            rows.append({**witness,'paired_joint_distance_m':paired,'initial_paired_joint_distance_m':start,'same_side_knee_distance_m':own,'inactive_elbow_to_target_knee_distance_m':other,'extended_knee_internal_angle_degrees':leg_angle,'elbow_knee_contact_claim':False})
        initial_angles={side:angle(subtraction(initial[side+'UpLeg'],initial[side+'Leg']),subtraction(initial[side+'Foot'],initial[side+'Leg']))for side in ['Left','Right']}
        assert all(abs(value-90)<.01 for value in initial_angles.values())
        (P/'cross-pair-witnesses.json').write_text(json.dumps({'source_sha256':source_sha,'motion_sha256':motion_sha,'initial_knee_internal_angles_degrees':initial_angles,'samples':rows,'basis':'Joint-centre distances in Blender world metres. Source says toward; no elbow-knee surface contact or clinical range is claimed.'},indent=2)+'\n')
    return build
if __name__=='__main__':print(json.dumps({'files':write()['files']}))
