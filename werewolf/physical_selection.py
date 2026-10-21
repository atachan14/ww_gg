"""Display partitions of physical P; never public evidence or policy inputs."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .seer_acquisition import normalize
from .calculation_budget import tick
from .evaluation_branch import physical_board


def counts(h,alive):
 mask=sum(1<<(p-1) for p in alive)
 roles=tuple((r&mask).bit_count() for r in h.roles)
 return (*roles,len(alive)-sum(roles))


def freeze(value):return tuple(freeze(v) for v in value) if isinstance(value,(tuple,list)) else value


@dataclass(frozen=True)
class PhysicalSelectionEvidence:
 kind:str
 selection:tuple
 def __call__(self,source):
  selection=freeze(self.selection)
  if self.kind=='composition':
   if len(selection)!=5 or any(type(v)is not int or v<0 for v in selection) or sum(selection)!=len(source.public.alive):raise ValueError('Invalid physical composition')
   keep=lambda h:counts(h,source.public.alive)==selection
  elif self.kind=='joint':
   if len(selection)!=3:raise ValueError('Invalid joint selection')
   night,wolves,scans=selection
   if type(night)is not int or night<1 or any(type(p)is not int or not 1<=p<=source.public.player_count for p in wolves) or any(len(s)!=2 or any(type(p)is not int or not 1<=p<=source.public.player_count for p in s) for s in scans):raise ValueError('Invalid joint selection')
   keep=lambda h:tuple(p for p in range(1,source.public.player_count+1) if h.roles[0]&(1<<(p-1)))==wolves and tuple(sorted((a.player,a.target) for a in h.acquisitions if a.day==night+1))==scans
  elif self.kind=='hypothesis':
   roles,records=selection
   keep=lambda h:h.roles==roles and tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions)==records
  else:raise ValueError('Unknown physical selection')
  tick(len(source.private.hypotheses))
  entries=tuple(h for h in source.private.hypotheses if keep(h))
  if not entries:raise ValueError('Physical selection has zero support')
  own=replace(source.private,hypotheses=normalize(entries))
  return replace(source,private=own,physical=physical_board(source.public,own,source.physical),board_data=None,provenance=None)
