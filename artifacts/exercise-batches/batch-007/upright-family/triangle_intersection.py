"""Exact triangle crossing kernel reused from accepted1512 verifier."""
from mathutils import Vector,geometry
TOL=1e-8
def intersect(a, b):
    n = (a[1] - a[0]).cross(a[2] - a[0])
    m = (b[1] - b[0]).cross(b[2] - b[0])
    if n.length < TOL or m.length < TOL:
        return False
    n.normalize()
    m.normalize()
    if abs(n.dot(m)) > 1 - 1e-09 and max((abs(n.dot(p - a[0])) for p in b)) < TOL:
        axis = max(range(3), key=lambda i: abs(n[i]))
        axes = [i for i in range(3) if i != axis]
        aa = [Vector((p[axes[0]], p[axes[1]])) for p in a]
        bb = [Vector((p[axes[0]], p[axes[1]])) for p in b]
        if any((geometry.intersect_point_tri_2d(p, *bb) for p in aa)) or any((geometry.intersect_point_tri_2d(p, *aa) for p in bb)):
            return True
        return any((geometry.intersect_line_line_2d(aa[i], aa[(i + 1) % 3], bb[j], bb[(j + 1) % 3]) is not None for i in range(3) for j in range(3)))
    for (edges, target) in [(a, b), (b, a)]:
        for i in range(3):
            start = edges[i]
            delta = edges[(i + 1) % 3] - start
            if delta.length_squared < TOL * TOL:
                continue
            hit = geometry.intersect_ray_tri(*target, delta, start, True)
            if hit is not None:
                factor = (hit - start).dot(delta) / delta.length_squared
                if -TOL <= factor <= 1 + TOL:
                    return True
    return False
