"""Closed fists in the original hand frame; fingers only, no skin/rest edits.

Actual-skin per-digit closure closes the prior hook; external thumb opposition follows
three source-length segments across the folded index, rather than pointing
normal to the palm. X is mirrored; the source thumb lies on negative hand Z.
"""
import math
from mathutils import Matrix,Quaternion,Vector

FINGER_ANGLES={'Index': [75.0, 61.3232421875, 35.0], 'Middle': [75.0, 62.12890625, 35.0], 'Ring': [75.0, 66.42578125, 35.0], 'Little': [75.0, 85.3955078125, 35.0]}
THUMB_X=2.9967041015625

def apply(a,d,angles=None,thumb_x=THUMB_X):
 angles=angles or FINGER_ANGLES
 for side,sign in [('Left',1),('Right',-1)]:
  hand=side+'Hand';palmar=a.rest[hand].to_3x3()@Vector((-sign,0,0))
  for name,(head,tail,parent,digit,index)in a.finger_specs.items():
   if not name.startswith(side)or digit=='Thumb':continue
   axis=a.rest[name].to_3x3().inverted()@(tail-head).normalized().cross(palmar).normalized()
   d[name]=d[parent]@a.rest[parent].inverted()@a.rest[name]@Quaternion(axis,math.radians(angles[digit][index])).to_matrix().to_4x4()
  inv=a.rest[hand].inverted();position=inv@a.heads[side+'Thumb1']
  directions=[(-sign*.35*thumb_x,.80,.48),(-sign*.35*thumb_x,.70,.62),(sign*.10*thumb_x,.45,.89)]
  for index,xyz in enumerate(directions,1):
   name=side+'Thumb'+str(index);base=(inv@a.rest[name]).to_quaternion();direction=Vector(xyz).normalized();q=(base@Vector((0,1,0))).rotation_difference(direction)@base
   d[name]=d[hand]@Matrix.Translation(position)@q.to_matrix().to_4x4();position+=direction*a.length[name]
 return d


def install_target(body,rig,punches,paired=()):
 """Install frozen additive source target; explicit1/0 weights per action."""
 import json,numpy as np
 from pathlib import Path
 recipe=json.loads((Path(__file__).parent/'fist-component.json').read_text());R=np.array([v.co[:]for v in body.data.vertices]);delta=np.zeros_like(R);delta[recipe['source_ids']]=recipe['source_deltas_m']
 assert not body.data.shape_keys
 body.shape_key_add(name='Basis',from_mix=False);key=body.shape_key_add(name=recipe['name'],from_mix=False);key.data.foreach_set('co',(R+delta).astype(np.float32).ravel());keys=body.data.shape_keys;keys.animation_data_create()
 import bpy
 for ID in [*punches,*paired]:
  action=bpy.data.actions['Exercise_'+ID];slot=next((s for s in action.slots if s.target_id_type=='KEY'),None)or action.slots.new(id_type='KEY',name='Closed fist dorsal MCP');keys.animation_data.action=action;keys.animation_data.action_slot=slot
  for frame in [1,151]:key.value=float(ID in punches);key.keyframe_insert('value',frame=frame)
 action=bpy.data.actions['Exercise_'+punches[0]];keys.animation_data.action=action;keys.animation_data.action_slot=next(s for s in action.slots if s.target_id_type=='KEY');key.value=1
 return recipe
