import sys,json,numpy as np
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from glb_runtime import Runtime
from glb_normals import patch_morph_normals,to_blender,unit

def patch(asset,report_path):
 r=Runtime(asset);s=r.sample(2.5);ids=r.source;rest=to_blender(r.pos);hip=(rest[:,0]>-.05)&(rest[:,0]<.34)&(rest[:,2]>.67)&(rest[:,2]<1.22);knee=(rest[:,0]>.025)&(rest[:,0]<.28)&(rest[:,2]>.36)&(rest[:,2]<.62)
 # Retain the existing normal transport outside the same local correction zones.
 C=np.array([[1,0,0],[0,0,1],[0,-1,0]])
 posed=to_blender(s['normals']);posed[hip|knee]=to_blender(s['geometric_normals'][hip|knee]);target=np.zeros((10582,3));target[ids]=posed;rot=np.zeros((10582,3,3));rot[ids]=C.T@s['blend'][:,:3,:3]@C
 metrics=patch_morph_normals(asset,target,rot);metrics['fit_time_seconds']=2.5;metrics['normal_correction_scope']='Selected left hip/knee neighborhoods; rest retains existing transport.';metrics['animated_phase_status']='Requires actual LBS normal proof at entry, hold, return.';report_path.write_text(json.dumps(metrics,indent=2)+'\n');return metrics

if __name__=='__main__':
 asset=P/'motion.glb'
 report=P/'normal-patch-report.json'
 print(json.dumps(patch(asset,report)))
