"""Actual whole-cage peak checks before final-cycle work."""
import numpy as np
from mathutils.bvhtree import BVHTree

def measure(body, xyz, motion):
    source = motion.R
    body.data.calc_loop_triangles()
    triangles = np.array([t.vertices[:] for t in body.data.loop_triangles])
    cross = np.cross(xyz[triangles[:, 1]] - xyz[triangles[:, 0]],
                     xyz[triangles[:, 2]] - xyz[triangles[:, 0]])
    area = np.linalg.norm(cross, axis=1) * .5
    regions = {}
    for polygon, attribute in zip(body.data.polygons, body.data.attributes['.sculpt_face_set'].data):
        regions.setdefault(attribute.value, set()).update(polygon.vertices)
    arm_ids = set.union(*(regions[k] for k in [9,10,11,12,20,21] +
                          [k for k in regions if 64 <= k < 104]))
    arms = np.zeros(len(source), bool)
    arms[list(arm_ids)] = True
    arm_faces = np.flatnonzero(np.all(arms[triangles], axis=1))
    legs = (source[:, 2] < 1.04) & (abs(source[:, 0]) < .32)
    leg_faces = np.flatnonzero(np.all(legs[triangles], axis=1))
    def tree(ids):
        return BVHTree.FromPolygons(xyz.tolist(), triangles[ids].tolist(), all_triangles=True)
    arm_leg = [(int(arm_faces[i]), int(leg_faces[j]))
               for i,j in tree(arm_faces).overlap(tree(leg_faces))]
    local = {}
    masks = {
        'shoulders': (abs(source[:,0]) > .08) & (abs(source[:,0]) < .39) & (source[:,2] > 1.12) & (source[:,2] < 1.53),
        'hips': (source[:,2] > .67) & (source[:,2] < 1.13),
        'knees': (source[:,2] > .34) & (source[:,2] < .65),
    }
    for name, mask in masks.items():
        ids = np.flatnonzero(np.all(mask[triangles], axis=1))
        surface = tree(ids)
        pairs = [(int(ids[i]), int(ids[j])) for i,j in surface.overlap(surface)
                 if i < j and not set(triangles[ids[i]]) & set(triangles[ids[j]])]
        local[name] = {'nonadjacent_crossings':len(pairs), 'triangle_pairs':pairs,
                       'minimum_area_m2':float(area[ids].min())}
    low = int(xyz[:,2].argmin())
    return {
        'minimum_body_source_id':low,
        'minimum_body_basis':source[low].tolist(),
        'minimum_triangle_area_m2':float(area.min()),
        'whole_arm_hand_vs_leg_crossings':arm_leg,
        'true_palms':{side:{'source_ids':frame['source_ids'],
                           'minimum_z':float(xyz[frame['source_ids'],2].min()),
                           'vertices_within5mm':int((abs(xyz[frame['source_ids'],2]) < .005).sum())}
                      for side,frame in motion.palm_frames.items()},
        'whole_head_minimum_z':float(xyz[motion.head,2].min()),
        'local':local,
        'component_weight':float(body.data.shape_keys.key_blocks['RestingHipVolume'].value) if body.data.shape_keys else 0.0,
    }
