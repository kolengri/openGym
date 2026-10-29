"""Frozen original-skin support and collar diagnostics for the half-kneel."""
import numpy as np
from peak_checks import measure

class SurfaceChecks:
    def __init__(self, body, landmarks=None):
        self.body=body
        self.R=np.array([v.co[:] for v in body.data.vertices])
        body.data.calc_loop_triangles()
        self.T=np.array([t.vertices[:] for t in body.data.loop_triangles])
        class Reference:pass
        self.motion=Reference();self.motion.R=self.R
        self.motion.head=np.flatnonzero(self.R[:,2]>1.55)
        self.motion.palm_frames={}
        self.patches=landmarks['patches'] if landmarks else None
        self.previous={}
    def freeze(self, X):
        R,T=self.R,self.T
        pp=X[T];cross=np.cross(pp[:,1]-pp[:,0],pp[:,2]-pp[:,0])
        unit=cross/np.linalg.norm(cross,axis=1)[:,None]
        patches={}
        for side,sign in [('Left',1),('Right',-1)]:
            candidates={'knee':(sign*R[:,0]>.05)&(R[:,2]>.43)&(R[:,2]<.57),
                        'dorsum':(sign*R[:,0]>.12)&(R[:,2]<.115)}
            for role,mask in candidates.items():
                faces=np.flatnonzero(np.all(mask[T],axis=1)&(unit[:,2]<-.35))
                assert len(faces)>0
                low=pp[faces,:,2].mean(1).min()
                faces=faces[pp[faces,:,2].mean(1)<low+.005]
                patches[side+'_'+role]={'indices':np.unique(T[faces]).tolist(),'triangles':faces.tolist(),'role':role,'side':side,'selection':'Actual native neutral floor-facing source faces within5mm of lowest local centroid.'}
            sole=(sign*R[:,0]>.12)&(R[:,2]<.012)
            for role,mask in [('heel',sole&(R[:,1]>.025)),('forefoot',sole&(R[:,1]<-.025))]:
                patches[side+'_'+role]={'indices':np.flatnonzero(mask).tolist(),'role':role,'side':side,'selection':'Original plantar source skin; heel and forefoot separate.'}
        self.patches=patches
    def measure(self, X, N, state):
        if self.patches is None:self.freeze(X)
        row=measure(self.body,X,self.motion)
        row['frame']=state['frame'];row['minimum_body_z']=float(X[:,2].min())
        failures=[]
        if row['minimum_body_z'] < -1e-6:failures.append('whole_body_floor')
        if row['minimum_triangle_area_m2']<=1e-12:failures.append('nonpositive_area')
        if row['whole_arm_hand_vs_leg_crossings']:failures.append('whole_arm_hand_vs_leg')
        support={};active=set()
        for name,patch in self.patches.items():
            side,role=patch['side'],patch['role'];kind=state['feet'][side]['support']
            supported=(role=='knee'and(state['q']<1e-7 or side!=state['active']))or(role=='dorsum'and kind=='dorsum')or(role in ['heel','forefoot']and kind=='sole')
            ids=patch['indices'];z=X[ids,2];center=X[ids].mean(0)
            value={'supported':supported,'indices_count':len(ids),'min_z':float(z.min()),'max_z':float(z.max()),'fraction_within12mm':float((abs(z)<.012).mean())}
            if supported:
                active.add(name)
                initial=self.previous.setdefault(name,center.copy())
                value['maximum_centroid_drift_m']=float(np.linalg.norm(center-initial))
                if z.min() < -1e-6 or z.min()>.012 or value['fraction_within12mm']<.2:failures.append(name+'_support')
                if role!='knee' and value['maximum_centroid_drift_m']>.005:failures.append(name+'_planted_drift')
            support[name]=value
        self.previous={name:value for name,value in self.previous.items()if name in active}
        row['supports']=support
        return row,failures
