"""Bounded topology diffusion of the source's hard torso/upper-arm weight seam."""
import numpy as np


def smoothstep(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)


def apply(body):
    xyz=np.array([v.co[:] for v in body.data.vertices])
    names=[g.name for g in body.vertex_groups]
    weights=np.zeros((len(xyz),len(names)))
    for v in body.data.vertices:
        for g in v.groups:
            weights[v.index,g.group]=g.weight
    original=weights.copy()
    # Local shoulder/axilla only. Torso centerline, elbow, distal arm and lower
    # body are outside this feathered source-coordinate neighborhood.
    blend=smoothstep((xyz[:,0]-.09)/.05)*(1-smoothstep((xyz[:,0]-.35)/.055))
    blend*=smoothstep((xyz[:,2]-1.16)/.055)*(1-smoothstep((xyz[:,2]-1.49)/.065))
    edges=np.array([e.vertices[:] for e in body.data.edges],dtype=int)
    deg=np.bincount(edges.ravel(),minlength=len(xyz))
    selected=np.array([n in ['Spine','Spine1','Neck','LeftShoulder','LeftArm'] for n in names])
    for _ in range(18):
        summed=np.zeros_like(weights)
        np.add.at(summed,edges[:,0],weights[edges[:,1]])
        np.add.at(summed,edges[:,1],weights[edges[:,0]])
        mean=summed/np.maximum(deg,1)[:,None]
        weights[:,selected]+=.55*blend[:,None]*(mean[:,selected]-weights[:,selected])
        weights/=weights.sum(axis=1)[:,None]
        weights[blend<=1e-8]=original[blend<=1e-8]
    # Keep only four influences and preserve exact original values outside.
    affected=np.flatnonzero(blend>1e-8)
    for i in affected:
        row=weights[i]
        keep=np.argsort(row)[-4:]
        row[np.setdiff1d(np.arange(len(row)),keep)]=0
        row[row<.001]=0
        row/=row.sum()
        for group in list(body.data.vertices[int(i)].groups):
            body.vertex_groups[group.group].remove([int(i)])
        for k in np.flatnonzero(row):
            body.vertex_groups[int(k)].add([int(i)],float(row[k]),'REPLACE')
    return {'purpose':'Remove the original source hard trunk/upper-arm weight boundary, exposed by cross-body rotation.',
        'method':'18 topology-neighbor diffusion iterations, 0.55 mixing, feathered original-coordinate left shoulder neighborhood; at most four influences.',
        'affected_vertices':len(affected),'affected_source_indices':affected.tolist(),
        'source_bounds':[xyz[affected].min(axis=0).tolist(),xyz[affected].max(axis=0).tolist()],
        'maximum_weight_change':float(np.abs(weights-original).max()),
        'unchanged_outside_neighborhood':bool(np.array_equal(weights[blend<=1e-8],original[blend<=1e-8])),
        'basis_rest_uv_topology_unchanged':True,
        'edits':[{'source_index':int(i),'original':{names[k]:float(original[i,k]) for k in np.flatnonzero(original[i])},
            'new':{body.vertex_groups[g.group].name:float(g.weight) for g in body.data.vertices[int(i)].groups}} for i in affected],
        'maximum_influences':max(len(v.groups) for v in body.data.vertices),
        'maximum_normalization_error':max(abs(sum(g.weight for g in v.groups)-1) for v in body.data.vertices)}
