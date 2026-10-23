"""Independent full-game scalar oracle for uniform policies with repeat guards.

Only counts are lumpable for win VALUE: public/private posteriors are not.
Prerequisites: uniform day executions, attacks uniformly among nonwolves,
exactly zero/one guard choosing uniformly among other living people, repeated
protection allowed, no self-bite or extra deaths/roles. Reports never influence
these fixed choices. A night with a successful guard does not remove a player.
"""
from fractions import Fraction as F
from functools import lru_cache

@lru_cache(None)
def value(n,w,h,phase):
 if w==0:return F(1)
 if w>=n-w:return F()
 if phase=='day':
  result=F(w,n)*value(n-1,w-1,h,'night')
  if h:result+=F(1,n)*value(n-1,w,0,'night')
  if n-w-h:result+=F(n-w-h,n)*value(n-1,w,h,'night')
  return result
 if phase!='night':raise ValueError('Day/night phase required')
 if not h:return value(n-1,w,0,'day')
 humans=n-w
 return (F(1,humans)*value(n-1,w,0,'day')+
         F(humans-1,humans)*(F(1,n-1)*value(n,w,1,'day')+
          F(n-2,n-1)*value(n-1,w,1,'day')))
