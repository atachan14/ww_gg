"""Interleaved local constructor comparison; not a full-search speed claim."""
from timeit import timeit
from fractions import Fraction as F
from dataclasses import replace
from statistics import median
from werewolf.exact import initial_board,replace_worlds

def old(board,worlds):
 projection={}
 for w,m,s,h,q in worlds:projection[w,m]=projection.get((w,m),F())+q
 return replace(board,belief=(),role_belief=tuple((w,m,q) for (w,m),q in sorted(projection.items())),world_belief=tuple(worlds),wolf_count=None)

if __name__=='__main__':
 for counts in [(5,1,0,1,0),(5,1,1,1,0),(6,2,1,1,1)]:
  board=initial_board(*counts);law=board.worlds;before=[];after=[]
  assert old(board,law)==replace_worlds(board,law,wolf_count=None)
  for _ in range(5):
   before.append(timeit(lambda:old(board,law),number=500))
   after.append(timeit(lambda:replace_worlds(board,law,wolf_count=None),number=500))
  print(dict(counts=counts,worlds=len(law),before=before,after=after,median_ratio=median(after)/median(before)))
