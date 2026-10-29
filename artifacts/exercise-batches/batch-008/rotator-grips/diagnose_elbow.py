"""Causal frame-roll evidence for the localized mixed-binding elbow fold."""
import bpy,sys,json,math,numpy as np
from pathlib import Path
from mathutils import Vector
sys.dont_write_bytecode=True
F=Path(__file__).resolve().parent;sys.path[:0]=[str(F),str(F.parent.parent/'batch-003')];import authoring as a
a.initialize();import importlib.util
spec=importlib.util.spec_from_file_location("baseline_elbow_motion",F/"timing-baseline/motion.py");motion=importlib.util.module_from_spec(spec);spec.loader.exec_module(motion)
rows=[]
for t in np.linspace(.70,1.25,112):
 d=motion.overhead(a,float(t));sh=d['LeftArm'].translation;el=d['LeftForeArm'].translation;wr=d['LeftHand'].translation;u=el-sh;l=wr-el;ou=a.tails['LeftArm']-a.heads['LeftArm'];of=a.tails['LeftForeArm']-a.heads['LeftForeArm'];normal=u.cross(l);original=ou.cross(of);angles={}
 for name,direction in[('LeftArm',u),('LeftForeArm',l)]:
  orig=ou if name=='LeftArm'else of;goal=(a.frame(direction,normal)@a.frame(orig,original).transposed()).to_quaternion()@a.rest[name].to_quaternion();axis=direction.normalized();n0=d[name].to_quaternion()@Vector((1,0,0));n1=goal@Vector((1,0,0));angles[name]=math.degrees(math.atan2(axis.dot(n0.cross(n1)),n0.dot(n1)))
 rows.append({'base_path_seconds':float(t),'coherent_plane_axial_delta_degrees':angles,'elbow_internal_degrees':math.degrees((-u).angle(l))})
(F/'elbow-roll-diagnosis.json').write_text(json.dumps({'scope':'Pure pose-frame comparison; no binding/skin changes. Original upper/lower bend plane mapped coherently to actual elbow plane.','samples':rows},indent=2)+'\n');print(json.dumps({'near_bad_pose':min(rows,key=lambda r:abs(r['base_path_seconds']-.9773094)),'ranges':{n:[min(r['coherent_plane_axial_delta_degrees'][n]for r in rows),max(r['coherent_plane_axial_delta_degrees'][n]for r in rows)]for n in['LeftArm','LeftForeArm']}}))
