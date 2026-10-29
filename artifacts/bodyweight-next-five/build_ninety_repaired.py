"""Author only the separate original-binding DQ90/90 preview asset.

The immutable previous-five source/GLB are never written. Runtime requires the
explicit dualQuaternion skinning adapter; ordinary LBS is not a quality target.
"""
import bpy,json,sys
from pathlib import Path
P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import ninety_pose as a


def main():
    binding=a.initialize()
    items=a.metadata()
    parameter_path=P/'ninety-contact-parameters.json'
    if parameter_path.exists():a.CONTACT_PARAMETERS=json.loads(parameter_path.read_text())['parameters']
    arm=next(m for m in a.body.modifiers if m.type=='ARMATURE')
    arm.use_deform_preserve_volume=True
    for modifier in a.body.modifiers:
        modifier.show_viewport=modifier.show_render=modifier.type=='ARMATURE'
    a.rig.animation_data_create()
    for item in items:
        item['skinning']='dualQuaternion';item['required_renderer']='Three.js approved dual-quaternion skinning adapter'
        item['review_status']='draft_DQ_requires_surface_geometry_and_visual_review'
        action=bpy.data.actions.new(item['action']);action.use_fake_user=True
        a.rig.animation_data.action=action
        previous={}
        for index in range(151):
            a.scene.frame_set(index+1);a.make_pose(item,index/30)
            for pb in a.rig.pose.bones:
                if pb.name in previous and previous[pb.name].dot(pb.rotation_quaternion)<0:pb.rotation_quaternion.negate()
                previous[pb.name]=pb.rotation_quaternion.copy()
                pb.keyframe_insert('location',frame=index+1)
                pb.keyframe_insert('rotation_quaternion',frame=index+1)
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
    assert len(a.rig.data.bones)==51 and a.body.data.shape_keys is None
    assert a.binding_hash(a.body,a.rig)==binding=='227ede3fc31d1a2b47ff40f20a4a7288fe7bb36179add23bae953993826c8b7b'
    a.rig.animation_data.action=bpy.data.actions['Exercise_10565'];a.scene.frame_set(1)
    a.scene.frame_end=151
    output=P/'ninety-repaired.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(output))
    (P/'ninety-clips.json').write_text(json.dumps(items,indent=2)+'\n')
    report={'source':str(a.SOURCE),'source_sha256':a.SOURCE_SHA,'output':str(output),'output_sha256':a.sha(output),
            'vertices':10582,'polygons':len(a.body.data.polygons),'bones':51,'binding_and_rest_geometry_sha256':binding,
            'original_binding_rest_uv_source_index_unchanged':True,'helpers':False,'morphs':False,
            'skinning':'dualQuaternion','required_renderer':'Three.js custom dual-quaternion adapter; standard GLB LBS playback is not the approved deformation.',
            'modifier_policy':'Only PreserveVolume Armature enabled. Original CorrectiveSmooth and Multires definitions retained but disabled; optional subdivision is separate authoring review, not runtime support truth.',
            'actions':[i['action'] for i in items],'duration_seconds':5,'preview_hold_seconds':1,'source_workout_hold_seconds':[20,30],
            'original_three_asset_immutable':{'blend_sha256':a.sha(P/'next-five.blend'),'glb_sha256':a.sha(P/'next-five.glb')},
            'authoring_files':{name:a.sha(P/name) for name in ['build_ninety_repaired.py','ninety_pose.py']},
            'contact_parameters_sha256':a.sha(parameter_path) if parameter_path.exists() else None,
            'status':'draft_requires_source_bound_DQ_surface_QA_and_primary_visual_acceptance'}
    (P/'ninety-source-identity.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


if __name__=='__main__':main()
