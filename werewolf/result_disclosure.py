"""Observed full-disclosure consistency; no generation likelihood or rescue."""
from copy import deepcopy
from fractions import Fraction
from .exact import Strategy,condition_claims,replace_worlds
MODEL='full-observed-v1'
class DisclosureInconsistent(ValueError):pass

def snapshot(g,board,claims):
 slot=2*(board.day-1)+(board.phase=='night');log=g.get('public_log')
 if log and log.get('version')==2:
  from .public_log_changes import declarations
  view=deepcopy(log);view['base_claims']=view['base_claims'][:slot+1];view['base_seer']=[r for r in view['base_seer'] if 2*(r['day']-1)<=slot];view['base_medium']=[r for r in view['base_medium'] if 2*(r['day']-1)<=slot];view['batches']=[b for b in view['batches'] if b['slot']<=slot]
  active,_=declarations(view);co=['latent']*g['players'];reported=set()
  for key,(_,e) in active.items():
   if key[0]=='co':co[e['player']-1]=e['role']
   elif e.get('target') is not None and e.get('color') is not None:reported.add((key[0],e['day'],e['player']))
  return tuple(co),reported
 from .report_publication import publication_slot
 reported={(kind,r['day'],r['reporter']) for kind,name in [('seer','seer_inputs'),('medium','reports')] for r in g.get(name,[]) if r.get('target') is not None and r.get('color') is not None and publication_slot(g,kind,r)<=slot}
 return claims,reported

def condition_observed(g,board,claims,cp,policy):
 if g.get('result_disclosure_model')!=MODEL:return board
 s=Strategy(**policy);co,reported=snapshot(g,board,claims)
 full=tuple(r for r in ('seer','medium') if s.disclosure_for(r)=='all')
 if not full:return board
 effective=tuple(co[i] if co[i] in full or claims[i] in full else claims[i] for i in range(g['players']))
 historical=tuple(c if c in full else 'latent' for c in co)
 try:board=condition_claims(board,historical,cp)
 except ValueError as exc:raise DisclosureInconsistent('全開示とCO義務が不整合です。') from exc
 missing={'seer':set(),'medium':set()}
 for p in board.alive:
  role=co[p-1]
  if role not in full:continue
  days=range(1,board.day+1) if role=='seer' else range(2,board.day+1)
  for day in days:
   if role=='seer' and day==1 and g['rules'].get('initial_seer','random_white')=='none':continue
   if (role,day,p) not in reported:missing[role].add(p)
 entries=tuple(w for w in board.worlds if not any(w[index]&(1<<(p-1)) for role,index in [('seer',2),('medium',1)] for p in missing[role]))
 mass=sum((w[-1] for w in entries),Fraction())
 if not mass:raise DisclosureInconsistent('全開示のCO者に未公開結果があり、整合する配役がありません。結果・開示設定・CO義務を確認してください。')
 return replace_worlds(board,tuple((*w[:-1],w[-1]/mass) for w in entries),claims=effective)
