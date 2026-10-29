"""Measured source/chest reach planes with an authored scapular motion share.

This rig has one shoulder bone from the neck base to the humeral head. It
therefore represents the clavicle/scapula complex, not an isolated clavicle.
The one-third share is an authored kinematic hypothesis; all axes and angular
excesses come from source and actual baseline reach frames, never world twist.
"""
import math
from mathutils import Vector,Matrix,Quaternion

def derive(a, matrices):
    matrices={name:Matrix(value)for name,value in matrices.items()}
    chest_delta=matrices['Spine1'].to_quaternion()@a.rest['Spine1'].to_quaternion().inverted()
    up=(a.tails['Spine1']-a.heads['Spine1']).normalized()
    result={}
    for side in ['Left','Right']:
        source_arm=(a.heads[side+'ForeArm']-a.heads[side+'Arm']).normalized()
        target_arm=chest_delta.inverted()@(matrices[side+'ForeArm'].translation-matrices[side+'Arm'].translation).normalized()
        elevation=lambda v:math.acos(max(-1,min(1,-up.dot(v))))
        source_elevation=elevation(source_arm);target_elevation=elevation(target_arm)
        upward=max(0,target_elevation-source_elevation)/3
        p0=(source_arm-up*source_arm.dot(up)).normalized()
        p1=(target_arm-up*target_arm.dot(up)).normalized()
        signed_yaw=math.atan2(up.dot(p0.cross(p1)),p0.dot(p1))
        clavicle=(a.heads[side+'Arm']-a.heads[side+'Shoulder']).normalized()
        upward_axis=clavicle.cross(up).normalized()
        result[side]={'upward_axis':list(upward_axis),'chest_up':list(up),'upward_radians':upward,'protraction_radians':signed_yaw/3,'source_elevation_degrees':math.degrees(source_elevation),'baseline_elevation_degrees':math.degrees(target_elevation),'baseline_reach_yaw_degrees':math.degrees(signed_yaw),'authored_motion_share':1/3}
    return result

def shoulder(a,side,torso_matrix,amount,parameters):
    name=side+'Shoulder';parent='Spine1'
    carried=torso_matrix@a.rest[parent].inverted()@a.rest[name]
    chest_delta=torso_matrix.to_quaternion()@a.rest[parent].to_quaternion().inverted()
    p=parameters[side]
    up=Quaternion(Vector(p['upward_axis']),p['upward_radians']*amount)
    protraction=Quaternion(Vector(p['chest_up']),p['protraction_radians']*amount)
    q=chest_delta@protraction@up@a.rest[name].to_quaternion()
    return Matrix.Translation(carried.translation)@q.to_matrix().to_4x4()
