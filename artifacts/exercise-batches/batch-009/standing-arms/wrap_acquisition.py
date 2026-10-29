"""Bounded anterior wrist detour over the immutable coherent 3995 route."""
import math
from mathutils import Matrix,Quaternion,Vector
from coherent_route import CoherentRoute,smooth


def clearance_gain(p):
    return smooth((p-.20)/.35)*(1.-smooth((p-.76)/.21))


class ClearanceRoute(CoherentRoute):
    def __init__(self, archive, amplitude):
        super().__init__(archive)
        self.amplitude=float(amplitude)

    def pose(self, frame):
        d,original_p=super().pose(frame)
        p=min(1.,original_p/self.peak)
        offset=self.amplitude*clearance_gain(p)
        if not offset:
            return d,original_p
        side='Left';tables=self.tables[side]
        shoulder=d[side+'Arm'].translation
        wrist=d[side+'Hand'].translation+Vector((0.,-offset,0.))
        axis=(wrist-shoulder).normalized();distance=(wrist-shoulder).length
        l1,l2=self.data[side+'_lengths']
        if not abs(l1-l2)<distance<l1+l2-1e-6:
            raise ValueError('Acquisition detour left the fixed-length reachable domain')
        along=(l1*l1-l2*l2+distance*distance)/(2.*distance)
        bend=self.transported(p,tables['axis'],tables['bend'],axis)
        bend=Quaternion(axis,float(self.data[side+'_bend_twist'])*smooth(p))@bend
        bend-=axis*bend.dot(axis);bend.normalize()
        elbow=shoulder+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along))
        for part,head,tail in [('Arm',shoulder,elbow),('ForeArm',elbow,wrist)]:
            direction=(tail-head).normalized()
            rotation=self.transported(p,tables[part+'_axes'],tables[part+'_frames'],direction)
            rotation=Quaternion(direction,float(self.data[side+'_'+part+'_twist'])*smooth(p))@rotation
            d[side+part]=Matrix.Translation(head)@rotation.to_matrix().to_4x4()
        local=[end[side+'ForeArm'].to_quaternion().inverted()@end[side+'Hand'].to_quaternion()for end in self.ends]
        rotation=d[side+'ForeArm'].to_quaternion()@local[0].slerp(local[1],smooth(p))
        d[side+'Hand']=Matrix.Translation(wrist)@rotation.to_matrix().to_4x4()
        for name,parent,local in self.fingers:
            if name.startswith(side):
                d[name]=d[parent]@local
        return d,original_p
