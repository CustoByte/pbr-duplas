"""Stable XYZ conversion for native Euler tracks near gimbal lock."""
import math

def stable_euler(q):
 w,x,y,z=q
 norm=math.sqrt(w*w+x*x+y*y+z*z)
 w,x,y,z=(a/norm for a in (w,x,y,z))
 r=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
    (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
    (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)))
 cy=math.hypot(r[0][0],r[1][0])
 if cy>1e-8:
  return (math.atan2(r[2][1],r[2][2]),math.atan2(-r[2][0],cy),math.atan2(r[1][0],r[0][0]))
 return (math.atan2(-r[1][2],r[1][1]),math.atan2(-r[2][0],cy),0.0)
