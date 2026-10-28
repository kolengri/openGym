"""Write source-backed runtime metadata without changing the authored asset."""
import json,hashlib
from pathlib import Path
P=Path(__file__).resolve().parent
ROOT=P.parents[4]
source=ROOT/'catalogue/exercises/1906.json'
record=json.loads(source.read_text())
clip={
'id':'1906','name':record['name'],'action':'Exercise_1906','duration':5,'duration_seconds':5,'frames':150,'fps':30,
'primary':['adductors'],'secondary':['groin','hip flexors'],'display_mode':'stretch','highlight_sides':{'adductors':['L'],'groin':['L'],'hip flexors':['L']},
'phases':[{'start':0,'end':2,'label':'Enter'},{'start':2,'end':3,'label':'Hold'},{'start':3,'end':5,'label':'Return'}],
'interpretation':'One anatomical left knee fall-out from supine straight legs. The left knee first flexes, then opens out under control; the left foot slides toward the pelvis and rolls onto its external border. The opposite leg stays naturally extended and the pelvis remains level. Relaxed open hands rest palms upward alongside the body. Optional hand assistance is omitted. The source20–30second stretch hold is compressed to a clearly labeled1second demonstration hold; repeat mirrored for the other side.',
'source_hold_recommendation_seconds':[20,30],
'source':{'path':'catalogue/exercises/1906.json','sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'text_source':'opengym','instructions':record['instructions'],'roles':{'target':record['target'],'secondaryMuscles':record['secondaryMuscles']},'media_used':False},
'explicit_staging':{'selected_anatomical_side':'L','mirror_note':'Repeat on the other side; this clip shows anatomical left only.','hand_assistance':'Omitted; source says if needed. No pulling or hand-knee contact is authored.','hand_pose':'Relaxed articulated fingers, palms up, backs of hands toward floor.','pelvis':'Fixed bone translation and orientation. A modest fixed posterior pelvic tilt and lumbar contour provide supine support without rolling.','opposite_leg':'Extended, small natural knee softness and slight external foot roll.','active_foot':'Illustrative heel slide during flexion and outer-border support during knee fall-out; source does not specify a planted sole.','angles':'Authored illustration, not source numerical ranges or clinical targets.'},
'muscle_mapping':{
 'adductors':{'role':'main_stretch','status':'partial_surface','regions':['adductor_longus.L','adductor_magnus_visible.L'],'notice':'Visible medial thigh surface proxy; deep origins and additional adductors omitted.'},
 'groin':{'role':'additional_stretch','status':'partial_surface','regions':['adductor_longus.L','adductor_magnus_visible.L'],'notice':'Shared medial thigh/adductor proxy, not a separate groin organ or precise deep-anatomy segmentation.'},
 'hip flexors':{'role':'additional_stretch','status':'deep_projection','regions':['sartorius.L','iliopsoas_projection.L'],'notice':'Limited anterior hip projection plus visible sartorius proxy; iliopsoas is deep, not exposed surface tissue.'}},
'visualization_notice':'Diffuse cyan on selected anatomical left regions only. Inactive skin stays uniform neutral. Cues are artistic stretch location, not EMG, temperature, force or measured recruitment.',
'provenance':{'body':'Accepted original CC0 Blender Studio Human Base Meshes1.4.1 continuous mannequin','binding_rest_uv_sha256':'227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b','motion':'New original procedural rig animation authored from repository exercise text. No Gym Visual stills, clips, derivative pose tracing or paid media generation.','notices':['catalogue/media/NOTICE.md','NOTICE.md','artifacts/human-animation-base/README.md']},
'correctives':{'count':1,'names':['LeftHipKnee_Soften'],'basis_rest_uv_weights_unchanged':True,'default_weights':[0],'animation':'One shared Exercise_1906 action; corrective zero at start/end and full before the hold.','geometry':'355feathered selected-left hip/knee vertices; original native CorrectiveSmooth cage target, inverse-LBSrest correction.','normals':'Exported NORMAL target fitted at hold through actual Three.js blendednormal matrix; inspect decoded actual LBS proof, since Blender5.2 import ignores morph NORMAL.'},
'review_status':'Authored prototype; requires primary live-runtime and visual acceptance. No clinical coaching or catalogue-wide production approval.'}
(P/'clip.json').write_text(json.dumps(clip,indent=2)+'\n')
