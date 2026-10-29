from pathlib import Path
import sys,json,bpy
F=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(F.parents[1]/'batch-003'))
import authoring as a
a.initialize()
sys.path.insert(0,str(Path.home()/'.codex/skills/blender-core/scripts'))
import env_report
(F/'environment.json').write_text(json.dumps(env_report.run(),indent=2)+'\n')
print('SOURCE',json.dumps({n:{'head':list(a.heads[n]),'tail':list(a.tails[n]),'length':a.length[n]}for n in ['Hips','Spine','Spine1','Head','RightUpLeg','RightLeg','RightFoot','RightToeBase','RightArm','RightForeArm','RightHand']}))
