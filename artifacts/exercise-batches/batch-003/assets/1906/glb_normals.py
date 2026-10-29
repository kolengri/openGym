"""Single morph normal transport fitted to the actual Three.js LBS equation.

Blender5.2 import omits morph NORMAL. Animated proof must decode the GLB and
apply actual morph weights plus the runtime blended normal matrix explicitly.
"""
import json
import struct
from pathlib import Path
import numpy as np

DTYPES={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1'}
COMPONENTS={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}


def read_glb(path):
    raw=Path(path).read_bytes()
    size,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4E4F534A
    doc=json.loads(raw[20:20+size])
    binary_size,binary_kind=struct.unpack_from('<II',raw,20+size)
    assert binary_kind==0x004E4942
    return doc,raw[28+size:28+size+binary_size]


def decode(doc,binary,index):
    acc=doc['accessors'][index]
    components=COMPONENTS[acc['type']]
    dtype=np.dtype(DTYPES[acc['componentType']])
    def view(index,offset,count,n,dtype):
        bv=doc['bufferViews'][index]
        return np.ndarray((count,n),dtype=dtype,buffer=binary,
            offset=bv.get('byteOffset',0)+offset,
            strides=(bv.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
    out=view(acc['bufferView'],acc.get('byteOffset',0),acc['count'],components,dtype) if 'bufferView'in acc else np.zeros((acc['count'],components),dtype=dtype)
    if 'sparse'in acc:
        sparse=acc['sparse'];ids=sparse['indices'];vals=sparse['values']
        ix=view(ids['bufferView'],ids.get('byteOffset',0),sparse['count'],1,np.dtype(DTYPES[ids['componentType']])).reshape(-1)
        out[ix]=view(vals['bufferView'],vals.get('byteOffset',0),sparse['count'],components,dtype)
    return out


def unit(vectors):
    return vectors/np.maximum(np.linalg.norm(vectors,axis=1)[:,None],1e-20)


def to_blender(vectors):
    return vectors[:,[0,2,1]]*np.array([1,-1,1])


def to_gltf(vectors):
    return vectors[:,[0,2,1]]*np.array([1,1,-1])


def default_normals(path):
    doc,binary=read_glb(path)
    primitive=doc['meshes'][0]['primitives'][0]
    source=decode(doc,binary,primitive['attributes']['_SOURCE_INDEX']).reshape(-1).astype(int)
    normal=decode(doc,binary,primitive['attributes']['NORMAL']).astype(np.float64)
    for weight,target in zip(doc['meshes'][0]['weights'],primitive['targets']):
        if 'NORMAL'in target:normal+=weight*decode(doc,binary,target['NORMAL'])
    return source,unit(to_blender(normal))


def patch_morph_normals(path,posed_normals_blender,blended_rotation_blender):
    """Set this one morph's NORMAL delta to reproduce the native posed normals.

    Three.js skinnormal_vertex applies R_blend * (N_basis + w * N_delta).
    The inverse-R target is fitted at full weight; animated intermediate weights require independent phase checks.
    """
    path=Path(path);doc,binary=read_glb(path)
    assert len(doc['meshes'])==1 and len(doc['meshes'][0]['weights'])==1
    primitive=doc['meshes'][0]['primitives'][0]
    assert len(primitive['targets'])==1 and 'NORMAL'in primitive['targets'][0]
    source=decode(doc,binary,primitive['attributes']['_SOURCE_INDEX']).reshape(-1).astype(int)
    base=decode(doc,binary,primitive['attributes']['NORMAL']).astype(np.float64)
    normal_accessor=primitive['targets'][0]['NORMAL']
    old=base+decode(doc,binary,normal_accessor)
    rotations=blended_rotation_blender[source]
    posed_normals=unit(posed_normals_blender[source])
    before=unit(np.einsum('nij,nj->ni',rotations,to_blender(old)))
    target_rest=unit(np.linalg.solve(rotations,posed_normals[...,None])[...,0])
    delta=(to_gltf(target_rest)-base).astype('<f4')
    assert np.isfinite(delta).all() and np.linalg.norm(delta,axis=1).max()<=2.001
    after=unit(np.einsum('nij,nj->ni',rotations,to_blender(base+delta)))
    angle=lambda value:np.degrees(np.arccos(np.clip(np.einsum('ni,ni->n',value,posed_normals),-1,1)))
    before_angle=angle(before);after_angle=angle(after)
    assert after_angle.max()<.05
    offset=len(binary)
    assert offset%4==0
    payload=delta.tobytes()
    doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(payload),'target':34962})
    doc['accessors'][normal_accessor]={'bufferView':len(doc['bufferViews'])-1,'componentType':5126,'count':len(source),'type':'VEC3'}
    binary+=payload
    doc['buffers'][0]['byteLength']=len(binary)
    document=json.dumps(doc,separators=(',',':')).encode()
    document+=b' '*((-len(document))%4)
    binary+=b'\x00'*((-len(binary))%4)
    total=12+8+len(document)+8+len(binary)
    raw=struct.pack('<4sII',b'glTF',2,total)+struct.pack('<II',len(document),0x4E4F534A)+document+struct.pack('<II',len(binary),0x004E4942)+binary
    path.write_bytes(raw)
    return {'method':'One peak-fitted morph NORMAL target inverse-transports the native posed geometric normals through the actual Three.js linear blended bone matrix; no positions, skin weights, Basis or rig rests change.',
        'angle_error_degrees_before':{str(q):float(np.percentile(before_angle,q)) for q in [50,90,95,99,100]},
        'angle_error_degrees_after':{str(q):float(np.percentile(after_angle,q)) for q in [50,90,95,99,100]},
        'normal_target_bytes':len(payload),'max_normal_delta':float(np.linalg.norm(delta,axis=1).max()),
        'blender_import_limitation':'Blender5.2 imp/mesh.py imports only morph POSITION and installs base custom normals. Readback must apply the transmitted default morph normal explicitly; raw importer shading is not a valid morph-normal proof.'}
