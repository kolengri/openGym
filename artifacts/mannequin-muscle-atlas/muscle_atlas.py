"""Illustrative muscle atlas for the CC0 Blender Studio realistic mannequin.

No anatomical segmentation or EMG is claimed. prepare() evaluates artist-authored
rest-space shapes ONCE; apply() only combines stored vertex-index weights.
The original body, sculpt, vertex order, modifiers and rig are never replaced.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

VERSION = "1.1.0"
EXPECTED_VERTICES = 10582
COLOR_ATTRIBUTE = "MuscleAtlas"
BASE_ATTRIBUTE = "MuscleAtlasBase"
WEIGHT_PREFIX = "MA_"
ROOT = Path(__file__).resolve().parent
_CACHE = {}
NEUTRAL_COLOR = np.array([0.49, 0.55, 0.58], dtype=np.float32)
PRIMARY_COLOR = np.array([0.82, 0.055, 0.025], dtype=np.float32)
SECONDARY_COLOR = np.array([0.98, 0.40, 0.045], dtype=np.float32)
STRETCH_COLOR = np.array([0.035, 0.57, 0.72], dtype=np.float32)


def _smooth(a, lo, hi):
    t = np.clip((a-lo)/(hi-lo), 0.0, 1.0)
    return t*t*(3.0-2.0*t)


def _polygon_field(x, z, points, feather=0.006):
    """Signed-distance field for an authored 2D surface projection, no topology edit."""
    inside = np.zeros(len(x), dtype=bool)
    distance = np.full(len(x), np.inf)
    px, pz = points[-1]
    for qx, qz in points:
        dx, dz = qx-px, qz-pz
        den = dx*dx+dz*dz
        t = np.clip(((x-px)*dx+(z-pz)*dz)/max(den, 1e-12), 0, 1)
        distance = np.minimum(distance, np.hypot(x-px-t*dx, z-pz-t*dz))
        crossing = ((qz > z) != (pz > z))
        inside ^= crossing & (x < (px-qx)*(z-qz)/(pz-qz+1e-20)+qx)
        px, pz = qx, qz
    return _smooth(np.where(inside, distance, -distance), -feather, feather)


def _spindle(x,z,a,b,radius,feather=0.006):
    ax,az=a; bx,bz=b
    dx,dz=bx-ax,bz-az
    t=((x-ax)*dx+(z-az)*dz)/(dx*dx+dz*dz)
    cross=np.abs((x-ax)*dz-(z-az)*dx)/np.hypot(dx,dz)
    width=radius*np.maximum(0,np.sin(np.pi*np.clip(t,0,1)))**0.65
    return _smooth(width-cross,-feather,feather)*_smooth(t,0,.08)*(1-_smooth(t,.92,1))


def _coordinates(body):
    out = np.empty((len(body.data.vertices),3), dtype=np.float32)
    body.data.vertices.foreach_get("co",out.ravel())
    return out


def _fingerprint(body):
    """Includes original coordinates and ordered polygon topology, not pose/rig state."""
    co = _coordinates(body)
    indices=np.empty(len(body.data.loops),dtype=np.int32)
    body.data.loops.foreach_get("vertex_index",indices)
    return hashlib.sha256(co.tobytes()+indices.tobytes()).hexdigest()


def _build_fields(co):
    x,y,z=np.abs(co[:,0]),co[:,1],co[:,2]
    # The source faces -Y. Gating follows the body's varying anterior/posterior
    # surface; this avoids a muscle wrapping around a limb into a broad patch.
    front=1-_smooth(y,-.003,.025)
    back=_smooth(y,.055,.085)
    leg_cy=np.interp(z,[0,.15,.3,.5,.65,.85,1.8],[.08,.105,.09,.045,.025,.015,.015])
    leg_front=1-_smooth(y-leg_cy,-.008,.024)
    leg_back=_smooth(y-leg_cy,.012,.042)
    side_gate=_smooth(x,.105,.15)
    regions={};meta={}
    def add(name,field,label,group,fiber="longitudinal",kind="superficial"):
        for sign,side in [(1,"L"),(-1,"R")]:
            key=f"{name}.{side}"
            w=field*_smooth(sign*co[:,0],-.002,.008)
            regions[key]=np.clip(w,0,1).astype(np.float32)
            meta[key]={"label":label,"side":side,"group":group,"visibility":kind,"fiber_direction":fiber}
    def poly(name,pts,gate,label,group,fiber="longitudinal",kind="superficial",feather=.005):
        add(name,_polygon_field(x,z,pts,feather)*gate,label,group,fiber,kind)
    def spindle(name,a,b,r,gate,label,group,fiber="longitudinal",kind="superficial"):
        add(name,_spindle(x,z,a,b,r)*gate,label,group,fiber,kind)
    poly('pectoralis_clavicular',[(.011,1.391),(.075,1.425),(.153,1.426),(.199,1.392),(.164,1.365),(.077,1.372),(.012,1.372)],front,'Pectoralis major, clavicular region','chest','fan')
    poly('pectoralis_sternal',[(.012,1.362),(.078,1.363),(.166,1.359),(.193,1.384),(.174,1.309),(.115,1.292),(.044,1.301),(.012,1.328)],front,'Pectoralis major, sternocostal region','chest','fan')
    # Deltoid heads are separated on the shoulder surface by anterior/lateral/posterior gates.
    shoulder=_polygon_field(x,z,[(.174,1.425),(.208,1.462),(.245,1.433),(.272,1.372),(.247,1.316),(.217,1.357)])
    anterior=1-_smooth(y,.008,.045);posterior=_smooth(y,.085,.115)
    middle=np.minimum(_smooth(y,.008,.045),1-_smooth(y,.085,.115))
    add('deltoid_anterior',shoulder*anterior,'Anterior deltoid','deltoids','pennate')
    add('deltoid_lateral',shoulder*middle,'Lateral deltoid','deltoids','pennate')
    add('deltoid_posterior',shoulder*posterior,'Posterior deltoid','deltoids','pennate')
    arm_front=1-_smooth(y,.018,.058);arm_back=_smooth(y,.045,.082)
    spindle('biceps',(.247,1.359),(.311,1.173),.037,arm_front,'Biceps brachii','biceps')
    spindle('brachialis_visible',(.266,1.322),(.328,1.171),.028,1-_smooth(y,.055,.085),'Brachialis visible lateral strip','biceps',kind='partial_surface')
    spindle('triceps_long',(.222,1.369),(.307,1.171),.037,arm_back,'Triceps brachii, long head region','triceps')
    spindle('triceps_lateral',(.264,1.371),(.335,1.185),.025,_smooth(y,.025,.06),'Triceps brachii, lateral head region','triceps')
    spindle('forearm_flexors',(.325,1.171),(.409,.955),.033,1-_smooth(y,.013,.045),'Forearm flexor compartment','forearm')
    spindle('forearm_extensors',(.339,1.166),(.416,.952),.032,_smooth(y,.02,.05),'Forearm extensor compartment','forearm')
    spindle('brachioradialis',(.348,1.183),(.412,1.005),.019,np.ones_like(x),'Brachioradialis','forearm')
    # Four separately addressable rectus blocks on each side; linea alba stays inert.
    for i,(lo,hi,w) in enumerate([(1.236,1.292,.055),(1.178,1.230,.058),(1.121,1.172,.055),(1.064,1.114,.046)],1):
        poly(f'rectus_abdominis_{i}',[(.009,lo+.009),(w-.009,lo),(w,lo+.015),(w,hi-.01),(w-.012,hi),(.009,hi-.003)],front,f'Rectus abdominis block {i} (superior to inferior)','abs',feather=.003)
    poly('external_oblique',[(.068,1.217),(.104,1.262),(.158,1.247),(.163,1.168),(.149,1.071),(.107,1.037),(.064,1.071),(.079,1.133)],np.maximum(front*.95,side_gate*(1-_smooth(y,.07,.1))),'External oblique','obliques','inferomedial')
    for i in range(4):
        zz=1.337-.027*i
        poly(f'serratus_{i+1}',[(.121,zz-.012),(.177,zz+.016),(.19,zz+.005),(.157,zz-.023)],side_gate*(1-_smooth(y,.04,.09)),f'Serratus anterior slip {i+1}','serratus','superolateral',feather=.003)
    poly('trapezius_upper',[(.008,1.56),(.049,1.521),(.19,1.454),(.17,1.427),(.095,1.457),(.015,1.431)],back,'Upper trapezius','trapezius','superolateral')
    poly('trapezius_middle',[(.009,1.422),(.088,1.449),(.165,1.414),(.142,1.365),(.065,1.372),(.009,1.393)],back,'Middle trapezius','trapezius','transverse')
    poly('trapezius_lower',[(.009,1.383),(.106,1.353),(.08,1.31),(.014,1.217)],back,'Lower trapezius','trapezius','superolateral')
    poly('rhomboid_projection',[(.028,1.415),(.098,1.43),(.133,1.377),(.078,1.333),(.03,1.355)],back,'Rhomboids, surface projection through trapezius','upper-back','inferolateral','deep_projection')
    poly('infraspinatus',[(.108,1.432),(.201,1.43),(.216,1.385),(.156,1.347),(.113,1.373)],back,'Infraspinatus region','upper-back','fan','partial_surface')
    spindle('teres_major',(.199,1.367),(.13,1.326),.025,back,'Teres major region','upper-back','superolateral')
    poly('latissimus_dorsi',[(.105,1.355),(.202,1.344),(.188,1.266),(.147,1.169),(.074,1.086),(.042,1.129),(.06,1.235)],np.maximum(back,side_gate*_smooth(y,.015,.055)),'Latissimus dorsi','upper-back','superolateral')
    spindle('erector_spinae',(.029,1.088),(.034,1.35),.023,back,'Erector spinae surface columns','lower-back')
    poly('gluteus_maximus',[(.021,.951),(.062,.997),(.126,1.009),(.174,.966),(.189,.901),(.158,.851),(.08,.858),(.027,.897)],_smooth(y,.07,.105),'Gluteus maximus','gluteal','inferolateral')
    poly('gluteus_medius_visible',[(.109,1.005),(.153,1.026),(.182,.99),(.188,.956),(.17,.939),(.128,.961)],_smooth(y,.012,.06)*_smooth(x,.105,.14),'Gluteus medius visible lateral region','gluteal','fan')
    spindle('tensor_fasciae_latae',(.164,.991),(.192,.858),.022,1-_smooth(y,.045,.085),'Tensor fasciae latae','gluteal')
    # Long tapered thigh masks leave groin, patella, seams and fascia uncovered.
    spindle('rectus_femoris',(.12,.873),(.151,.552),.024,leg_front,'Rectus femoris','quadriceps','bipennate')
    poly('vastus_lateralis',[(.163,.855),(.201,.798),(.209,.7),(.187,.602),(.16,.548),(.147,.589),(.165,.709),(.148,.801)],1-_smooth(y-leg_cy,.02,.065),'Vastus lateralis','quadriceps','inferomedial')
    poly('vastus_medialis',[(.094,.769),(.113,.725),(.139,.603),(.134,.534),(.115,.516),(.085,.557),(.081,.617)],leg_front,'Vastus medialis','quadriceps','inferolateral')
    spindle('sartorius',(.165,.885),(.073,.566),.013,leg_front,'Sartorius','hip-flexors','oblique')
    poly('adductor_longus',[(.031,.861),(.075,.838),(.099,.756),(.081,.659),(.053,.678),(.028,.76)],1-_smooth(y,.045,.075),'Adductor longus and medial compartment','adductors','inferolateral')
    poly('adductor_magnus_visible',[(.03,.824),(.069,.783),(.104,.65),(.093,.581),(.059,.662),(.022,.751)],_smooth(y,.035,.075),'Adductor magnus visible medial region','adductors','inferolateral','partial_surface')
    poly('iliopsoas_projection',[(.057,1.015),(.098,1.02),(.133,.953),(.106,.898),(.071,.934)],front,'Iliopsoas, illustrative surface projection','hip-flexors','longitudinal','deep_projection')
    spindle('biceps_femoris',(.162,.857),(.187,.526),.036,leg_back,'Biceps femoris','hamstring')
    spindle('semitendinosus',(.097,.855),(.111,.526),.027,leg_back,'Semitendinosus / medial hamstring region','hamstring')
    spindle('semimembranosus_visible',(.067,.823),(.086,.56),.022,leg_back,'Semimembranosus visible medial region','hamstring',kind='partial_surface')
    spindle('gastrocnemius_medial',(.14,.477),(.162,.245),.031,leg_back,'Medial gastrocnemius head','calves','pennate')
    spindle('gastrocnemius_lateral',(.19,.46),(.204,.27),.027,leg_back,'Lateral gastrocnemius head','calves','pennate')
    spindle('soleus_lateral',(.211,.383),(.209,.145),.018,_smooth(y-leg_cy,-.004,.022),'Soleus visible lateral strip','calves','pennate')
    spindle('soleus_medial',(.122,.363),(.158,.143),.018,_smooth(y-leg_cy,-.004,.022),'Soleus visible medial strip','calves','pennate')
    spindle('tibialis_anterior',(.167,.468),(.188,.123),.021,leg_front,'Tibialis anterior','tibialis')
    spindle('sternocleidomastoid',(.031,1.548),(.066,1.636),.011,1-_smooth(y,-.025,.01),'Sternocleidomastoid','neck','oblique')
    return regions,meta


def _base_colors(co,weights,meta, *, fiber_scale=1.0):
    """Neutral gray anatomy with fixed seams and broad illustrative fiber contrast."""
    keys=list(weights)
    # Deep structures are hidden in the neutral atlas; activating one reveals its
    # explicitly documented projection, rather than claiming superficial anatomy.
    dominant=np.zeros(len(co),dtype=np.int32);coverage=np.zeros(len(co),dtype=np.float32)
    for i,k in enumerate(keys):
        if meta[k]['visibility']=='deep_projection':continue
        sel=weights[k]>coverage;dominant[sel]=i;coverage=np.maximum(coverage,weights[k])
    x,y,z=np.abs(co[:,0]),co[:,1],co[:,2]
    fiber=np.ones(len(co),dtype=np.float32)
    phase=np.zeros(len(co),dtype=np.float32)
    for i,k in enumerate(keys):
        select=dominant==i;style=meta[k]['fiber_direction'];group=meta[k]['group']
        if style=='fan':p=np.arctan2(z-1.365,x-.19)*9 if group=='chest' else np.arctan2(z-1.39,x-.2)*8
        elif style in ('inferomedial','inferolateral','oblique'):p=(x*1.8+z)*150
        elif style=='superolateral':p=(z-x*.65)*165
        elif style=='transverse':p=z*210
        elif style in ('pennate','bipennate'):p=(x+abs(z%0.04-.02)*.4)*250
        else:p=x*245+z*16
        phase[select]=p[select]
    # Deliberately broad enough for the source cage's sampling density. The
    # texture path draws finer fibers from these same cached region directions.
    raw_fiber=.80+.20*(.5+.5*np.cos(phase*fiber_scale))
    fiber=1-coverage*(1-raw_fiber)
    seam=1-_smooth(coverage,.16,.70)
    region_tone=np.array([.31,.37,.40],dtype=np.float32)
    inert=NEUTRAL_COLOR
    color=inert[None,:]*(1-coverage[:,None])+region_tone[None,:]*coverage[:,None]
    color*=fiber[:,None]*(1-.13*seam[:,None]*_smooth(coverage,.03,.18)[:,None])
    return color.astype(np.float32),fiber


def _float_attribute(mesh,name,values):
    a=mesh.attributes.get(name)
    if a is None:a=mesh.attributes.new(name=name,type='FLOAT',domain='POINT')
    if a.domain!='POINT' or a.data_type!='FLOAT':raise ValueError(f'Incompatible existing attribute {name}')
    a.data.foreach_set('value',np.asarray(values,np.float32).ravel())
    return a


def _color_attribute(mesh,name,colors):
    a=mesh.color_attributes.get(name)
    if a is None:a=mesh.color_attributes.new(name=name,type='FLOAT_COLOR',domain='POINT')
    if a.domain!='POINT' or a.data_type!='FLOAT_COLOR':raise ValueError(f'Incompatible existing color attribute {name}')
    rgba=np.column_stack([colors,np.ones(len(colors),dtype=np.float32)])
    a.data.foreach_set('color',rgba.ravel())
    return a


def prepare(body, *, force=False, install_material=False):
    """Return dict[region_id, float32[N]]; preserve geometry and all vertex indices.

    Must be called on the unmodified 1.8 m source rest cage. An Armature modifier
    and vertex groups may already be present. Weights are persisted as MA_* point
    attributes; subsequent loads reuse them. force=True rebuilds only the atlas.
    """
    if body.type!='MESH' or len(body.data.vertices)!=EXPECTED_VERTICES:
        raise ValueError(f'Atlas needs the 10582-vertex Blender Studio source cage; got {getattr(body,"type",None)} / {len(body.data.vertices)}')
    key=body.data.as_pointer()
    if key in _CACHE and not force:return _CACHE[key]['weights']
    co=_coordinates(body)
    sig=_fingerprint(body)
    info_path=ROOT/'region-map.json'
    mapping=json.loads(info_path.read_text()) if info_path.exists() else None
    expected=mapping['body']['rest_sha256'] if mapping else None
    if expected and sig!=expected:raise ValueError('Rest coordinates or ordered topology differ from the authored atlas; preserve the original source cage.')
    weights,meta=_build_fields(co)
    if not all(np.isfinite(v).all() for v in weights.values()):
        raise ValueError('Atlas field contains non-finite weights')
    if body.get('muscle_atlas_version')==VERSION and not force:
        for k in weights:
            a=body.data.attributes.get(WEIGHT_PREFIX+k)
            if a and a.domain=='POINT':a.data.foreach_get('value',weights[k])
    else:
        for k,v in weights.items():_float_attribute(body.data,WEIGHT_PREFIX+k,v)
    base,fiber=_base_colors(co,weights,meta)
    neutral=np.broadcast_to(NEUTRAL_COLOR,(len(co),3)).copy()
    _color_attribute(body.data,BASE_ATTRIBUTE,neutral)
    active=_color_attribute(body.data,COLOR_ATTRIBUTE,neutral)
    body.data.color_attributes.active_color=active
    _float_attribute(body.data,'MA_Fiber',fiber)
    # Linear rest-space fiber coordinates deform as ordinary point attributes.
    # Fine material stripes therefore move with the skin without a per-frame solve.
    vec=body.data.attributes.get('MA_Rest') or body.data.attributes.new(name='MA_Rest',type='FLOAT_VECTOR',domain='POINT')
    vec.data.foreach_set('vector',co.ravel())
    body['muscle_atlas_version']=VERSION
    body['muscle_atlas_rest_sha256']=sig
    body['muscle_atlas_notice']='Illustrative artist-authored surface masks; not segmentation, EMG, or a muscle recruitment measurement.'
    _CACHE[key]={'weights':weights,'meta':meta,'base':base,'fiber':fiber,'signature':sig}
    if install_material:ensure_material(body)
    return weights


def resolve_names(names, *, strict=False):
    """Resolve catalogue strings or exact region IDs; return explicit exceptions."""
    if isinstance(names,str):names=[names]
    mapping=json.loads((ROOT/'region-map.json').read_text())
    result={};unresolved=[];notices=[]
    for raw in names or ():
        name=str(raw).strip().lower()
        exact=next((k for k in mapping['regions'] if k.lower()==name),None)
        if exact:result[exact]=1.;continue
        entry=mapping['mappings'].get(name)
        if entry is None:unresolved.append(str(raw));continue
        for region in entry['regions']:result[region]=max(result.get(region,0),1.)
        if entry['status']!='surface':notices.append({'name':name,'status':entry['status'],'reason':entry['reason']})
    if strict and unresolved:raise ValueError('Unknown muscle names: '+', '.join(unresolved))
    return {'regions':result,'unknown':unresolved,'notices':notices}


def apply(body, primary_names=(), secondary_names=(), strength=1.0, *, stretch_names=(), strict=False, show_inactive_anatomy=False):
    """Color stored rest weights. No spatial solving or geometry changes per call.

    Primary=red, secondary=amber, stretch=cyan. Unselected skin is uniform gray;
    selected regions retain their fiber and boundary detail. strength is a visual
    blend [0,1], NOT physiological activation. show_inactive_anatomy=True opts in
    to the complete neutral anatomy drawing. Return mappings, notices and counts.
    """
    weights=prepare(body);data=_CACHE[body.data.as_pointer()]
    strength=float(strength)
    if not np.isfinite(strength) or not 0<=strength<=1:raise ValueError('strength must be a finite visual blend in [0,1]')
    primary=resolve_names(primary_names,strict=strict);secondary=resolve_names(secondary_names,strict=strict)
    stretch=resolve_names(stretch_names,strict=strict)
    n=len(body.data.vertices)
    p=np.maximum.reduce([weights[k] for k in primary['regions']]) if primary['regions'] else np.zeros(n,np.float32)
    s=np.maximum.reduce([weights[k] for k in secondary['regions']]) if secondary['regions'] else np.zeros(n,np.float32)
    t=np.maximum.reduce([weights[k] for k in stretch['regions']]) if stretch['regions'] else np.zeros(n,np.float32)
    color=data['base'].copy() if show_inactive_anatomy else np.broadcast_to(NEUTRAL_COLOR,(n,3)).copy()
    detail=data['fiber'][:,None]
    t=(t*strength*.85)[:,None]
    color=color*(1-t)+(STRETCH_COLOR[None,:]*detail)*t
    s=(s*strength*.82)[:,None];p=(p*strength*.94)[:,None]
    color=color*(1-s)+(SECONDARY_COLOR[None,:]*detail)*s
    color=color*(1-p)+(PRIMARY_COLOR[None,:]*detail)*p
    a=_color_attribute(body.data,COLOR_ATTRIBUTE,color)
    body.data.color_attributes.active_color=a
    body.data.update()
    if 'texture' in data:_apply_texture(data['texture'],primary,secondary,stretch,strength,show_inactive_anatomy=show_inactive_anatomy)
    return {'primary':primary,'secondary':secondary,'stretch':stretch,'strength':strength,'vertex_count':n,'color_attribute':COLOR_ATTRIBUTE,'show_inactive_anatomy':bool(show_inactive_anatomy)}


def ensure_material(body):
    """Optional EEVEE/Cycles/export material; Workbench uses VERTEX shading.

    Appends and assigns one atlas-owned material, preserving existing slot IDs.
    It reads the same activation color attribute. Fiber detail lives in selected
    colors only; no global procedural bump is applied to inactive skin.
    """
    import bpy
    name='MAT_MuscleAtlas_Illustrative'
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    attr=nodes.new('ShaderNodeVertexColor');attr.layer_name=COLOR_ATTRIBUTE
    bs=nodes.new('ShaderNodeBsdfPrincipled');bs.inputs['Roughness'].default_value=.72
    bs.inputs['Metallic'].default_value=0
    bs.inputs['Specular IOR Level'].default_value=.20
    links.new(attr.outputs['Color'],bs.inputs['Base Color'])
    out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs['BSDF'],out.inputs['Surface'])
    idx=next((i for i,m in enumerate(body.data.materials) if m==mat),None)
    if idx is None:body.data.materials.append(mat);idx=len(body.data.materials)-1
    for p in body.data.polygons:p.material_index=idx
    return mat


def region_metadata(body):
    prepare(body)
    return _CACHE[body.data.as_pointer()]['meta']


def prepare_texture(body, *, resolution=(4096,2048)):
    """Sharper optional Workbench path; adds UV/image, never changes vertices.

    Existing UVs are copied into a normalized 9x4 tile layout, preserving the
    source UVMap. Raster surface coordinates and sparse region texel fields are
    solved only here. apply() then updates colors, with no projection or solving.
    Use scene.display.shading.color_type='TEXTURE'. Blender-generated images and
    the UV map are embedded in a saved .blend. Native vertex fields remain valid.
    """
    import bpy
    prepare(body);data=_CACHE[body.data.as_pointer()]
    if 'texture' in data:return data['texture']['image']
    width,height=map(int,resolution)
    if width<512 or height<256:raise ValueError('Texture atlas needs at least 512x256 pixels')
    mesh=body.data;source=mesh.uv_layers.get('UVMap')
    if source is None:raise ValueError('Original source UVMap is required for texture preparation')
    uv=np.empty((len(mesh.loops),2),np.float32);source.uv.foreach_get('vector',uv.ravel())
    uv=uv/np.array([9.,4.],np.float32)
    target=mesh.uv_layers.get('MuscleAtlasUV') or mesh.uv_layers.new(name='MuscleAtlasUV')
    target.uv.foreach_set('vector',uv.ravel());mesh.uv_layers.active=target;target.active_render=True
    co=_coordinates(body);mesh.calc_loop_triangles()
    raster=np.full((height,width,3),np.nan,np.float32)
    for tri in mesh.loop_triangles:
        st=uv[list(tri.loops)]*np.array([width,height]);xyz=co[list(tri.vertices)]
        lo=np.maximum(0,np.floor(st.min(0)).astype(int));hi=np.minimum([width-1,height-1],np.ceil(st.max(0)).astype(int))
        if np.any(hi<lo):continue
        xx,yy=np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
        ax,ay=st[0];bx,by=st[1];cx,cy=st[2]
        den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-10:continue
        a=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den
        b=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;c=1-a-b
        inside=(a>=-1e-6)&(b>=-1e-6)&(c>=-1e-6)
        block=raster[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
        block[inside]=(a[...,None]*xyz[0]+b[...,None]*xyz[1]+c[...,None]*xyz[2])[inside]
    # Four texels of padding avoid white UV seams under bilinear filtering.
    for _ in range(4):
        valid=np.isfinite(raster[:,:,0]);out=raster.copy()
        for dy,dx in [(1,0),(-1,0),(0,1),(0,-1)]:
            shifted=np.roll(raster,(dy,dx),(0,1));take=~valid&np.isfinite(shifted[:,:,0]);out[take]=shifted[take]
        raster=out
    indices=np.flatnonzero(np.isfinite(raster[:,:,0]).ravel()).astype(np.int32)
    points=raster.reshape(-1,3)[indices];del raster
    texweights,meta=_build_fields(points)
    if not all(np.isfinite(v).all() for v in texweights.values()):raise ValueError('Non-finite texture field')
    # Much finer fibers than possible on the source's sparse torso cage. They
    # follow each authored region's fan/oblique/pennate direction and stay off
    # inert head, hands, fascia and feet.
    base,fiber=_base_colors(points,texweights,meta,fiber_scale=5.0)
    sparse={}
    for k,v in texweights.items():
        idx=np.flatnonzero(v>.001).astype(np.int32);sparse[k]=(idx,v[idx])
    del texweights
    name=f'MuscleAtlas_{body.name}'
    image=bpy.data.images.get(name)
    if image is not None and tuple(image.size)!=(width,height):bpy.data.images.remove(image);image=None
    if image is None:image=bpy.data.images.new(name,width=width,height=height,alpha=True,float_buffer=False)
    image.colorspace_settings.name='Non-Color'
    data['texture']={'image':image,'indices':indices,'weights':sparse,'base':base,'fiber':fiber,'shape':(height,width),'painted_texels':len(indices)}
    mat=ensure_material(body);nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Linear';nodes.active=tex
    uvnode=nodes.new('ShaderNodeUVMap');uvnode.uv_map='MuscleAtlasUV';links.new(uvnode.outputs['UV'],tex.inputs['Vector']);links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    empty={'regions':{}}
    _apply_texture(data['texture'],empty,empty,empty,1)
    return image


def _apply_texture(texture,primary,secondary,stretch,strength, *, show_inactive_anatomy=False):
    n=len(texture['base'])
    def field(selection):
        out=np.zeros(n,np.float32)
        for k in selection['regions']:
            idx,v=texture['weights'][k];out[idx]=np.maximum(out[idx],v)
        return out
    color=texture['base'].copy() if show_inactive_anatomy else np.broadcast_to(NEUTRAL_COLOR,(n,3)).copy()
    fiber=texture['fiber'][:,None]
    for selected,tone,gain in [(stretch,STRETCH_COLOR,.85),(secondary,SECONDARY_COLOR,.82),(primary,PRIMARY_COLOR,.94)]:
        w=(field(selected)*strength*gain)[:,None];color=color*(1-w)+tone[None,:]*fiber*w
    height,width=texture['shape'];pixels=np.empty((height*width,4),np.float32);pixels[:,:3]=NEUTRAL_COLOR;pixels[:,3]=1
    pixels[texture['indices'],:3]=color
    texture['image'].pixels.foreach_set(pixels.ravel());texture['image'].update()


def export_texture(body, filepath, *, pack=True):
    """Write current color image as an sRGB PNG; optionally pack current pixels.

    Set the scene to Standard / None / exposure 0 / gamma 1 for neutral transfer.
    The build script uses these settings. No render or lighting is baked here.
    """
    import bpy
    prepare_texture(body);im=_CACHE[body.data.as_pointer()]['texture']['image']
    dest=Path(filepath);dest.parent.mkdir(parents=True,exist_ok=True)
    im.save_render(str(dest),scene=bpy.context.scene)
    if pack:im.pack()
    return str(dest)


def export_role_mask(body, filepath, primary_names=(), secondary_names=(), *, stretch_names=()):
    """Write a linear RGB role-weight PNG: R primary, G secondary, B stretch.

    Import this mask as non-color data. Channels preserve overlaps so the viewer
    decides role priority; atlas.apply uses primary > secondary > stretch.
    """
    import bpy
    prepare_texture(body);texture=_CACHE[body.data.as_pointer()]['texture']
    height,width=texture['shape'];pixels=np.zeros((height*width,4),np.float32);pixels[:,3]=1
    for channel,names in enumerate([primary_names,secondary_names,stretch_names]):
        selected=resolve_names(names,strict=True);values=np.zeros(len(texture['base']),np.float32)
        for k in selected['regions']:
            idx,v=texture['weights'][k];values[idx]=np.maximum(values[idx],v)
        pixels[texture['indices'],channel]=values
    im=bpy.data.images.new('MuscleAtlas_role_export',width=width,height=height,alpha=True)
    im.colorspace_settings.name='Non-Color';im.pixels.foreach_set(pixels.ravel())
    dest=Path(filepath);dest.parent.mkdir(parents=True,exist_ok=True)
    im.filepath_raw=str(dest);im.file_format='PNG';im.save()
    bpy.data.images.remove(im)
    return str(dest)
