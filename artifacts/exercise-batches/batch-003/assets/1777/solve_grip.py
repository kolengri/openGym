"""Bounded pose-only spacing search on the unchanged original linear hand skin."""
import ast
import json
import math
import sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
P = Path(__file__).resolve().parent
sys.path.insert(0, str(P.parents[1]))
import authoring as a
a.initialize()
body, rig, scene = a.body, a.rig, a.scene
tree = ast.parse((P/'build_motion.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ['amount', 'pose']], type_ignores=[]), str(P/'build_motion.py'), 'exec'))
R = np.array([v.co[:] for v in body.data.vertices])
body.data.calc_loop_triangles()
tri = np.array([t.vertices for t in body.data.loop_triangles])
names = [b.name for b in rig.data.bones]
restinv = np.array([b.matrix_local.inverted() for b in rig.data.bones])
groupnames = {g.index: g.name for g in body.vertex_groups}
index = {n: i for i, n in enumerate(names)}
weight = np.zeros((len(R), 4))
joint = np.zeros((len(R), 4), int)
for v in body.data.vertices:
    for i, g in enumerate(v.groups):
        weight[v.index, i] = g.weight
        joint[v.index, i] = index[groupnames[g.group]]
homo = np.column_stack((R, np.ones(len(R))))
masks = [(R[:, 0] > .375) & (R[:, 2] < .965), (R[:, 0] < -.375) & (R[:, 2] < .965)]
trials = []
for span in [.150, .153, .156, .159]:
    for row in [.010, .014, .018]:
        for normal in [.010, .020, .030, .040]:
            for angles in [[10, 55, 30], [15, 60, 35], [20, 65, 35]]:
                GRIP = {'wrist_halfspan': span, 'row_offset': row, 'normal_offset': normal,
                        'finger_angles': angles, 'thumb_angles': [5, 25, 15]}
                d = pose(2.5)
                transform = np.array([d[n] for n in names]) @ restinv
                xyz = np.zeros((len(R), 4))
                for k in range(4):
                    xyz += weight[:, k, None]*np.einsum('nij,nj->ni', transform[joint[:, k]], homo)
                trees = [BVHTree.FromPolygons(xyz[:, :3].tolist(), tri[np.all(mask[tri], axis=1)].tolist(), all_triangles=True) for mask in masks]
                intersections = len(trees[0].overlap(trees[1]))
                if intersections == 0:
                    distance = min(trees[1].find_nearest(tuple(v[:3]))[3] for v in xyz[masks[0]])
                    finger_x = [float((d['Left'+digit+'3']@a.rest['Left'+digit+'3'].inverted()@a.tails['Left'+digit+'3']).x) for digit in ['Index', 'Middle', 'Ring', 'Little']]
                    trials.append({'grip': GRIP.copy(), 'intersections': 0, 'closest_surface_gap_m': distance,
                                   'left_fingertip_x': finger_x,
                                   'score': span + abs(normal-.020)*.1 + abs(distance-.002)*2})
trials.sort(key=lambda q: q['score'])
(P/'grip-solve.json').write_text(json.dumps({'tested': 144, 'zero_intersection_candidates': len(trials), 'best': trials[:12]}, indent=2)+'\n')
print(json.dumps({'tested': 144, 'zero_intersection_candidates': len(trials), 'best': trials[:3]}))
