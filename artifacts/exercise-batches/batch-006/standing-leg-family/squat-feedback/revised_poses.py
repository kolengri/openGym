"""Only3479 sequencing changes; the accepted pose/contact implementation is reused."""
import math
from mathutils import Vector
from poses import StandingLegPoses as AcceptedStandingLegPoses, ease

class StandingLegPoses(AcceptedStandingLegPoses):
 def state(self,id,f):
  if id!='3479':return super().state(id,f)
  t=f/30;half=min(4,t if t<4 else t-4);side='Left' if t<4 else 'Right';sign=1 if side=='Left' else -1;feet={}
  for ss,sgn in [('Left',1),('Right',-1)]:
   fq=self.flatq(ss);feet[ss]={'ankle':Vector((sgn*.16,.078,self.foot_height(ss,fq,fq))),'footq':fq,'toeq':fq,'support':'whole_sole'}
  # Finish the two-foot squat and stand before transferring onto the support
  # leg. The previously accepted kick/tap/retract trajectory then runs intact.
  squat=ease(half/.90) if half<=.90 else (1-ease((half-.90)/.80) if half<=1.70 else 0)
  transfer=ease((half-1.70)/.25) if half<=1.95 else (1 if half<=3.85 else 1-ease((half-3.85)/.15))
  u=half-1.35
  kick=ease((u-.60)/.50) if u<=1.10 else (1 if u<=1.55 else 1-ease((u-1.55)/.95))
  contact=ease((u-1.0)/.20) if u<=1.20 else (1 if u<=1.55 else 1-ease((u-1.55)/.35))
  root=Vector((-sign*.10*transfer,.04+.26*squat,.959-.504*squat-.029*transfer+.0003));pitches=[22*squat,24*squat,20*squat,10*squat,4*squat];bend=sign*30*kick
  active=feet[side];flat=self.flatq(side);fq=flat.slerp(self.bladeq(side),kick)
  full=Vector((sign*.76,.078,.97));tap=Vector((sign*.58,.078,1.08));end=full.lerp(tap,contact);active['ankle']=active['ankle'].lerp(end,kick);active['footq']=active['toeq']=fq;active['support']='airborne' if kick>1e-7 else 'whole_sole'
  return {'id':id,'frame':f,'half':half,'side':side,'sign':sign,'root':root,'pitches':pitches,'bend':bend,'squat':squat,'kick':kick,'contact':contact,'support_transfer':transfer,'duration_seconds':8,'feet':feet}
